import flet as ft
import flet_camera as fc
import cv2
import numpy as np
import re
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable
from typing import cast
from pyzbar.pyzbar import decode

from pages.theme import ThemeColors


def build_nav_item(icon: ft.IconData, label: str, selected: bool = False, compact: bool = False) -> ft.Column:
    """Return a bottom navigation item with active/inactive visual state."""

    icon_color = "#2E5D4E" if selected else ThemeColors.TEXT_INACTIVE
    text_color = "#2E5D4E" if selected else ThemeColors.TEXT_INACTIVE
    weight = ft.FontWeight.BOLD if selected else ft.FontWeight.W_500
    nav_item_controls: list[ft.Control] = [ft.Icon(icon=icon, color=icon_color, size=24)]
    if not compact:
        nav_item_controls.append(ft.Text(label, size=12, color=text_color, weight=weight))
    return ft.Column(
        spacing=2 if not compact else 0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=nav_item_controls,
    )


class BarcodeScannerController:
    """Owns camera lifecycle and barcode decoding state for the scan page."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.camera = None
        self.running = False
        self.streaming_supported = False
        self.status_text = None
        self.result_text = None
        self.capture_button = None
        self.manual_entry_field = None
        self.debug_log_field = None
        self.lookup_overlay = None
        self.on_barcode_detected: Callable[[str], Awaitable[bool]] | None = None
        self.on_product_name_detected: Callable[[str], Awaitable[bool]] | None = None
        self.last_failed_barcode: str | None = None
        self.lookup_in_progress = False
        self.debug_log_lines: list[str] = []
        self.debug_log_path = Path("runtime_debug.log")

    def bind_controls(self, controls: dict):
        # Called after scan UI is built so async handlers can update the
        # visible status/result text and interact with camera/capture controls.
        self.camera = controls["camera"]
        self.status_text = controls["status_text"]
        self.result_text = controls["result_text"]
        self.capture_button = controls["capture_button"]
        self.manual_entry_field = controls.get("manual_entry_field")
        self.debug_log_field = controls.get("debug_log_field")
        self.lookup_overlay = controls.get("lookup_overlay")
        self.running = False
        self.streaming_supported = False
        self.last_failed_barcode = None
        self.lookup_in_progress = False
        self.append_debug("bind_controls", "Scan controls bound successfully")

    def append_debug(self, step: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.debug_log_lines.append(f"[{timestamp}] {step}: {message}")
        # Keep recent history while preventing unbounded growth.
        self.debug_log_lines = self.debug_log_lines[-120:]

        log_line = self.debug_log_lines[-1]
        try:
            with self.debug_log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(log_line + "\n")
        except Exception:
            pass

        # Also emit to stdout so attached terminals still receive traces.
        print(log_line)

        if self.debug_log_field is not None:
            try:
                if getattr(self.debug_log_field, "page", None) is None:
                    return

                self.debug_log_field.value = "\n".join(self.debug_log_lines)
                self.page.update()
            except Exception:
                # Scan page may have been replaced; keep logs in memory and
                # reattach to a fresh field the next time scan view is built.
                self.debug_log_field = None

    def set_barcode_detected_handler(self, handler: Callable[[str], Awaitable[bool]] | None):
        # Main application provides this callback to perform product lookup and
        # route to the product details page when a valid food item is found.
        self.on_barcode_detected = handler

    def set_product_name_detected_handler(self, handler: Callable[[str], Awaitable[bool]] | None):
        # Optional callback for manual text search by product name.
        self.on_product_name_detected = handler

    async def handle_decoded_barcode(self, barcode_value: str):
        self.append_debug("handle_decoded_barcode", f"Received barcode {barcode_value}")

        # Ignore duplicate failed barcodes until the user scans a different code.
        if barcode_value == self.last_failed_barcode:
            self.append_debug("handle_decoded_barcode", "Barcode matches last failed value; prompting rescan")
            if self.status_text is not None:
                self.status_text.value = "Please scan a different barcode"
            if self.result_text is not None:
                self.result_text.value = "This barcode is not a food item in Open Food Facts. Scan again."
            self.page.update()
            return

        if self.on_barcode_detected is None:
            self.append_debug("handle_decoded_barcode", "No lookup callback attached; showing scanned value only")
            if self.result_text is not None:
                self.result_text.value = f"Scanned: {barcode_value}"
            self.page.update()
            return

        if self.lookup_in_progress:
            self.append_debug("handle_decoded_barcode", "Lookup already in progress; skipping duplicate request")
            return

        self.lookup_in_progress = True
        if self.lookup_overlay is not None:
            self.lookup_overlay.visible = True
        if self.status_text is not None:
            self.status_text.value = "Checking product in Open Food Facts..."
        if self.result_text is not None:
            self.result_text.value = f"Barcode: {barcode_value}"
        self.page.update()
        self.append_debug("open_food_facts_lookup", "Lookup request started")

        try:
            is_food = await self.on_barcode_detected(barcode_value)
            self.append_debug("open_food_facts_lookup", f"Lookup completed; is_food={is_food}")
            if is_food:
                self.last_failed_barcode = None
                return

            self.last_failed_barcode = barcode_value
            if self.status_text is not None:
                self.status_text.value = "Not a food product"
            if self.result_text is not None:
                self.result_text.value = "This barcode is not in Open Food Facts. Please scan again."
            self.page.update()
        except Exception as exc:
            self.append_debug("open_food_facts_lookup_error", f"{type(exc).__name__}: {exc}")
            if self.status_text is not None:
                self.status_text.value = "Lookup error"
            if self.result_text is not None:
                self.result_text.value = f"Could not verify barcode ({exc}). Please scan again."
            self.page.update()
        finally:
            self.lookup_in_progress = False
            if self.lookup_overlay is not None and getattr(self.lookup_overlay, "page", None) is not None:
                self.lookup_overlay.visible = False
                self.page.update()
            self.append_debug("open_food_facts_lookup", "Lookup request finished")

    async def search_manual_barcode(self, e):
        # Manual entry accepts barcode numbers or product names so users can
        # continue even when labels are damaged or codes are missing.
        if self.manual_entry_field is None:
            self.append_debug("manual_entry", "Manual entry field is not available")
            return

        raw_input = str(self.manual_entry_field.value or "").strip()
        self.append_debug("manual_entry", f"Raw input received: '{raw_input}'")
        if not raw_input:
            if self.status_text is not None:
                self.status_text.value = "Enter product name or barcode"
            if self.result_text is not None:
                self.result_text.value = "Examples: milk, yogurt, rice, 04963406, 012345678905"
            self.page.update()
            return

        # Allow common separators, then test barcode-style digits first.
        normalized = re.sub(r"[^0-9]", "", raw_input)
        self.append_debug("manual_entry", f"Normalized input: '{normalized}'")

        if re.fullmatch(r"\d{8,14}", normalized):
            await self.handle_decoded_barcode(normalized)
            return

        product_query = raw_input.strip()
        if len(product_query) < 2:
            self.append_debug("manual_entry", "Input rejected; product name too short")
            if self.status_text is not None:
                self.status_text.value = "Enter more details"
            if self.result_text is not None:
                self.result_text.value = "Type at least 2 characters for product name search."
            self.page.update()
            return

        if self.on_product_name_detected is None:
            self.append_debug("manual_entry", "No product-name lookup callback attached")
            if self.status_text is not None:
                self.status_text.value = "Search unavailable"
            if self.result_text is not None:
                self.result_text.value = "Product name search is not configured."
            self.page.update()
            return

        if self.lookup_in_progress:
            self.append_debug("manual_entry", "Lookup already in progress; skipping duplicate request")
            return

        self.lookup_in_progress = True
        if self.lookup_overlay is not None:
            self.lookup_overlay.visible = True
        if self.status_text is not None:
            self.status_text.value = "Searching by product name..."
        if self.result_text is not None:
            self.result_text.value = f"Query: {product_query}"
        self.page.update()

        try:
            is_food = await self.on_product_name_detected(product_query)
            if not is_food:
                if self.status_text is not None:
                    self.status_text.value = "No matching food found"
                if self.result_text is not None:
                    self.result_text.value = "Try a more specific product name or enter barcode."
                self.page.update()
        except Exception as exc:
            self.append_debug("manual_name_lookup_error", f"{type(exc).__name__}: {exc}")
            if self.status_text is not None:
                self.status_text.value = "Lookup error"
            if self.result_text is not None:
                self.result_text.value = f"Could not search product name ({exc})."
            self.page.update()
        finally:
            self.lookup_in_progress = False
            if self.lookup_overlay is not None and getattr(self.lookup_overlay, "page", None) is not None:
                self.lookup_overlay.visible = False
                self.page.update()

    def camera_supported_on_platform(self) -> bool:
        # In browser builds, the camera widget can be used directly.
        if bool(getattr(self.page, "web", False)):
            return True

        # For native runtime we intentionally target mobile platforms
        # (Android/iOS) where Flet camera integration is expected to work.
        platform_name = str(self.page.platform).lower()
        return "android" in platform_name or "ios" in platform_name

    @staticmethod
    def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=1.5, threshold=0):
        # Sharpen edges before barcode decoding so narrow bars are easier to
        # separate from background noise.
        blurred = cv2.GaussianBlur(image, kernel_size, sigma)
        sharpened = float(amount + 1) * image - float(amount) * blurred
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        if threshold > 0:
            low_contrast_mask = np.absolute(image - blurred) < threshold
            np.copyto(sharpened, image, where=low_contrast_mask)
        return sharpened

    async def preprocess_for_pyzbar(self, img):
        # Convert to grayscale to reduce dimensionality and stabilize decode.
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Bilateral filter smooths noise while preserving barcode edges.
        gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

        # Edge enhancement improves weak or slightly blurred captures.
        gray = self.unsharp_mask(gray)

        # Adaptive thresholding handles mixed lighting conditions by computing
        # local thresholds instead of using one global threshold.
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,
            3,
        )

        # Add white border so codes near image edges still have clean margins
        # for pyzbar's detector window.
        padding = 20
        gray = cv2.copyMakeBorder(
            gray,
            padding,
            padding,
            padding,
            padding,
            cv2.BORDER_CONSTANT,
            value=255,
        )
        return gray

    async def process_stream_frame(self, e):
        # Called for each streaming frame when live image stream is active.
        image_bytes = e.bytes
        if not image_bytes:
            return

        try:
            # Convert raw bytes into an OpenCV BGR frame.
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            # Ignore malformed frames and keep the stream alive.
            self.append_debug("stream_decode", "Failed to decode stream frame bytes")
            return

        if frame is None:
            return

        # Mirror frame to match what users see in most front-facing previews.
        frame = cv2.flip(frame, 1)
        gray = await self.preprocess_for_pyzbar(frame)
        barcodes = decode(gray)

        if self.result_text is None:
            return

        if barcodes:
            barcode = barcodes[0]
            barcode_value = barcode.data.decode("utf-8", "ignore")
            self.append_debug("stream_decode", f"Barcode decoded from stream: {barcode_value}")
            await self.handle_decoded_barcode(barcode_value)
        else:
            self.result_text.value = "No barcode scanned yet"

        self.page.update()

    async def capture_photo_and_scan(self, e):
        # Photo mode is used when live stream decoding is unavailable.
        if not self.running:
            self.append_debug("photo_scan", "Capture requested while camera not running")
            if self.status_text is not None:
                self.status_text.value = "Camera not running"
            if self.result_text is not None:
                self.result_text.value = "Start the camera first, then take a photo"
            self.page.update()
            return

        if self.status_text is not None:
            self.status_text.value = "Capturing photo..."
        if self.result_text is not None:
            self.result_text.value = "Processing image..."
        self.page.update()

        if self.camera is None:
            return

        try:
            # Capture one still image, then run the same decode pipeline as
            # the streaming path.
            image_bytes = await self.camera.take_picture()
            if not image_bytes:
                raise RuntimeError("No image was captured")

            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError("Could not read the captured image")

            frame = cv2.flip(frame, 1)
            gray = await self.preprocess_for_pyzbar(frame)
            barcodes = decode(gray)

            if barcodes:
                barcode = barcodes[0]
                barcode_value = barcode.data.decode("utf-8", "ignore")
                self.append_debug("photo_scan", f"Barcode decoded from photo: {barcode_value}")
                await self.handle_decoded_barcode(barcode_value)
            elif self.result_text is not None:
                self.append_debug("photo_scan", "No barcode found in captured photo")
                self.result_text.value = "No barcode found in the photo"

            if self.status_text is not None:
                self.status_text.value = "Photo captured"
            self.page.update()
        except Exception as exc:
            self.append_debug("photo_scan_error", f"{type(exc).__name__}: {exc}")
            # Keep errors user-friendly while still surfacing the underlying
            # exception in status for troubleshooting.
            if self.status_text is not None:
                self.status_text.value = f"Photo error: {exc}"
            if self.result_text is not None:
                self.result_text.value = "Could not read the captured photo"
            self.page.update()

    async def start_camera(self, e):
        # Guard against duplicate starts from repeated button presses.
        if self.running:
            self.append_debug("start_camera", "Start ignored because camera is already running")
            return

        if self.status_text is not None:
            self.status_text.value = "Requesting camera access..."
        if self.result_text is not None:
            self.result_text.value = "Opening the camera..."
        self.page.update()

        if self.camera is None:
            self.append_debug("start_camera", "Camera control is not available on this page")
            return

        try:
            # Discover cameras and initialize the first available device.
            cameras = await self.camera.get_available_cameras()
            if not cameras:
                raise RuntimeError("No camera devices were found")
            self.append_debug("start_camera", f"Detected {len(cameras)} camera device(s)")

            await self.camera.initialize(cameras[0], fc.ResolutionPreset.MEDIUM, enable_audio=False)

            supports_streaming = await self.camera.supports_image_streaming()
            self.streaming_supported = supports_streaming
            self.append_debug("start_camera", f"Image streaming supported={supports_streaming}")

            if supports_streaming:
                # Best UX: continuous live decoding from incoming frames.
                self.camera.on_stream_image = self.process_stream_frame
                await self.camera.start_image_stream()
                self.running = True
                if self.capture_button is not None:
                    self.capture_button.disabled = True
                if self.status_text is not None:
                    self.status_text.value = "Scanning..."
                if self.result_text is not None:
                    self.result_text.value = "Live barcode scanning is active"
            else:
                # Fallback mode: allow manual still-photo capture for decode.
                self.running = True
                if self.capture_button is not None:
                    self.capture_button.disabled = False
                if self.status_text is not None:
                    self.status_text.value = "Camera preview ready"
                if self.result_text is not None:
                    self.result_text.value = (
                        "Live barcode scanning is not available on this platform. Use Take Photo when ready."
                    )

            self.page.update()
        except Exception as exc:
            self.append_debug("start_camera_error", f"{type(exc).__name__}: {exc}")
            # Distinguish browser permission/network constraints from native
            # camera errors for clearer user guidance.
            self.running = False
            if self.status_text is not None:
                if bool(getattr(self.page, "web", False)):
                    self.status_text.value = "Camera unavailable in browser"
                else:
                    self.status_text.value = f"Camera error: {exc}"

            if self.result_text is not None:
                if bool(getattr(self.page, "web", False)):
                    self.result_text.value = "Allow camera permission in the browser and use localhost/https."
                else:
                    self.result_text.value = "Please allow camera access and make sure a webcam is connected."
            self.page.update()

    async def _safe_camera_call(self, camera_call, *args):
        # Camera plugin APIs throw when the control is not mounted on page.
        # This guard avoids scheduling calls after the scan view has been
        # replaced (e.g., navigating to product details from manual search).
        if self.camera is None:
            return

        if getattr(self.camera, "page", None) is None:
            return

        try:
            await camera_call(*args)
        except Exception as exc:
            self.append_debug("stop_camera_call_error", f"{type(exc).__name__}: {exc}")

    def stop_camera(self):
        # Reset state first so UI and handlers treat camera as inactive.
        self.running = False
        self.append_debug("stop_camera", "Stop requested")

        if self.camera is not None:
            try:
                # Stop stream when active; each call is protected so one
                # failure does not block remaining cleanup work.
                if self.streaming_supported:
                    self.page.run_task(self._safe_camera_call, self.camera.stop_image_stream)
            except Exception:
                pass

            try:
                self.page.run_task(self._safe_camera_call, self.camera.pause_preview)
            except Exception:
                pass

            try:
                # Remove selected camera description to release device binding.
                self.page.run_task(self._safe_camera_call, self.camera.set_description, None)
            except Exception:
                pass

        self.streaming_supported = False

        if self.capture_button is not None:
            self.capture_button.disabled = True
        if self.status_text is not None:
            self.status_text.value = "Camera stopped"
        if self.result_text is not None:
            self.result_text.value = "No barcode scanned yet"


def build_scan_shell(
    metrics: dict,
    camera_is_supported: bool,
    recent_products: list[dict] | None,
    on_back_click,
    on_home_click,
    on_pantry_click,
    on_me_click,
    on_recent_product_click,
    on_clear_recent_click,
    on_start_camera,
    on_stop_camera,
    on_take_photo,
    on_manual_search,
) -> dict:
    # Build the complete scanner shell and return both the root container and
    # individual controls needed by asynchronous camera handlers in MAIN.PY.
    status_text = ft.Text(value="Camera ready", size=13, color=ThemeColors.GREEN_TEXT, weight=ft.FontWeight.W_500)
    result_text = ft.Text(
        value="No barcode scanned yet",
        size=16,
        weight=ft.FontWeight.BOLD,
        color="#0A1726",
    )

    camera = fc.Camera(preview_enabled=True, expand=True) if camera_is_supported else None

    if camera_is_supported:
        # Scanner control actions remain unchanged; only visual composition is updated.
        capture_button = ft.Button(
            content=ft.Text("Take Photo"),
            disabled=True,
            on_click=on_take_photo,
            style=ft.ButtonStyle(
                bgcolor="#FFFFFF",
                color=ThemeColors.TEXT_PRIMARY,
            ),
        )
        action_controls: list[ft.Control] = cast(
            list[ft.Control],
            [
                ft.Button(
                    content=ft.Text("Start Camera"),
                    on_click=on_start_camera,
                    style=ft.ButtonStyle(bgcolor="#2E5D4E", color=ThemeColors.BRAND_ON_PRIMARY),
                ),
                ft.Button(
                    content=ft.Text("Stop Camera"),
                    on_click=on_stop_camera,
                    style=ft.ButtonStyle(bgcolor="#ECEFF3", color="#101010"),
                ),
                capture_button,
            ],
        )
        preview_content: ft.Control = camera if camera is not None else ft.Container()
    else:
        # Informational fallback for runtimes where camera preview is
        # unsupported, while keeping navigation available.
        capture_button = ft.Button(content=ft.Text("Take Photo"), disabled=True)
        status_text.value = "Camera preview is unavailable on this platform"
        result_text.value = "This app targets Web, Android, and iOS"
        action_controls = cast(
            list[ft.Control],
            [
                ft.Button(
                    content=ft.Text("Back Home"),
                    on_click=on_back_click,
                    style=ft.ButtonStyle(bgcolor="#2E5D4E", color=ThemeColors.BRAND_ON_PRIMARY),
                )
            ],
        )
        preview_content = ft.Container(
            alignment=ft.Alignment(0, 0),
            content=ft.Text(
                "Camera preview is supported on Web, Android, and iOS.",
                color="#3E4758",
                size=16,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    preview_frame_width = int(metrics["shell_width"] * (0.9 if metrics["is_desktop"] else 0.92))

    lookup_overlay = ft.Container(
        visible=False,
        expand=True,
        bgcolor="#AAFFFFFF",
        alignment=ft.Alignment(0, 0),
        content=ft.Container(
            bgcolor="#FFFFFF",
            border_radius=14,
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            content=ft.Row(
                tight=True,
                spacing=10,
                controls=[
                    ft.ProgressRing(width=18, height=18, stroke_width=3, color=ThemeColors.BRAND_PRIMARY),
                    ft.Text(
                        "Looking up product details...",
                        size=14,
                        color="#1F2A3A",
                        weight=ft.FontWeight.W_600,
                    ),
                ],
            ),
        ),
    )

    scanner_surface = ft.Container(
        height=350 if metrics["is_desktop"] else 300,
        border_radius=22,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor="#FFFFFF",
        content=ft.Stack(
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Container(
                        width=preview_frame_width,
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        content=preview_content,
                    ),
                ),
                ft.Container(
                    top=14,
                    left=0,
                    right=0,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Container(
                        bgcolor="#FFFFFF",
                        border_radius=22,
                        padding=ft.Padding(left=14, top=8, right=14, bottom=8),
                        content=ft.Row(
                            tight=True,
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED, size=18, color=ThemeColors.GREEN_TEXT),
                                ft.Text(
                                    "Point your camera at the product barcode",
                                    size=16 if metrics["is_desktop"] else 14,
                                    color=ThemeColors.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                        ),
                    ),
                ),
                lookup_overlay,
            ],
        ),
    )

    manual_entry_field = ft.TextField(
        expand=True,
        hint_text="e.g., Greek yogurt, Basmati rice, 04963406",
        dense=True,
        prefix_icon=ft.Icons.SEARCH,
        on_submit=on_manual_search,
        border_radius=14,
        border_color="#D4DCE5",
        focused_border_color=ThemeColors.BRAND_PRIMARY,
        bgcolor="#FFFFFF",
        color="#152238",
    )

    manual_header: ft.Control
    if metrics["is_desktop"] or metrics["is_tablet"]:
        manual_header = ft.Row(
            spacing=12,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Manually Enter Product Name or Barcode",
                            size=24 if metrics["is_desktop"] else 18,
                            weight=ft.FontWeight.BOLD,
                            color="#0A1A12",
                        ),
                        ft.Text(
                            "Type product name or barcode to continue.",
                            size=14,
                            color="#2E3747",
                        ),
                    ],
                ),
            ],
        )
    else:
        manual_header = ft.Column(
            spacing=8,
            controls=[
                ft.Text(
                    "Manually Enter Product Name or Barcode",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color="#0A1A12",
                ),
                ft.Text(
                    "Type product name or barcode to continue.",
                    size=14,
                    color="#2E3747",
                ),
            ],
        )

    manual_search_controls: ft.Control
    if metrics["is_desktop"] or metrics["is_tablet"]:
        manual_search_controls = ft.Row(
            spacing=10,
            controls=cast(
                list[ft.Control],
                [
                    manual_entry_field,
                    ft.Button(
                        content=ft.Text("Search"),
                        on_click=on_manual_search,
                        style=ft.ButtonStyle(
                            bgcolor="#2E5D4E",
                            color=ThemeColors.BRAND_ON_PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=14),
                        ),
                    ),
                ],
            ),
        )
    else:
        manual_search_controls = ft.Column(
            spacing=10,
            controls=cast(
                list[ft.Control],
                [
                    manual_entry_field,
                    ft.Container(
                        alignment=ft.Alignment(1, 0),
                        content=ft.Button(
                            content=ft.Text("Search"),
                            on_click=on_manual_search,
                            style=ft.ButtonStyle(
                                bgcolor="#2E5D4E",
                                color=ThemeColors.BRAND_ON_PRIMARY,
                                shape=ft.RoundedRectangleBorder(radius=14),
                            ),
                        ),
                    ),
                ],
            ),
        )

    manual_entry_card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=ThemeColors.CARD_RADIUS_OUTER,
        padding=ThemeColors.CARD_PADDING,
        content=ft.Column(
            spacing=ThemeColors.SECTION_SPACING,
            controls=[
                manual_header,
                manual_search_controls,
                ft.Text(
                    "Examples: Product names -> milk, greek yogurt, brown rice | Barcodes -> 04963406, 012345678905",
                    size=12,
                    color=ThemeColors.TEXT_SECONDARY,
                ),
            ],
        ),
    )

    freshness_card = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=ThemeColors.CARD_RADIUS_OUTER,
        padding=ThemeColors.CARD_PADDING,
        content=ft.Row(
            spacing=12,
            controls=[
                ft.Text(
                    "Adding products helps you track freshness, reduce food waste, and share with others!",
                    expand=True,
                    size=14,
                    color="#213125",
                    weight=ft.FontWeight.W_600,
                ),
            ],
        ),
    )

    recent_items = [item for item in list(recent_products or []) if isinstance(item, dict)][:5]

    if recent_items:
        recent_rows: list[ft.Control] = []

        for recent_product in recent_items:
            recent_name = str(recent_product.get("product_name") or "Unknown product")
            recent_image = recent_product.get("best_image_url")

            recent_image_control: ft.Control
            if isinstance(recent_image, str) and recent_image:
                recent_image_control = ft.Image(
                    src=recent_image,
                    width=64,
                    height=64,
                    border_radius=12,
                )
            else:
                recent_image_control = ft.Container(
                    width=64,
                    height=64,
                    border_radius=12,
                    bgcolor="#F1F4F8",
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text("🥫", size=28),
                )

            recent_rows.append(
                ft.GestureDetector(
                    on_tap=lambda _, product=recent_product: on_recent_product_click(product),
                    content=ft.Container(
                        bgcolor="#F7FAFC",
                        border_radius=ThemeColors.CARD_RADIUS_INNER,
                        padding=12,
                        content=ft.Row(
                            spacing=12,
                            controls=[
                                recent_image_control,
                                ft.Column(
                                    expand=True,
                                    spacing=4,
                                    controls=[
                                        ft.Text(
                                            recent_name,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            size=16,
                                            color=ThemeColors.TEXT_PRIMARY,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            "Tap to view food facts",
                                            size=13,
                                            color=ThemeColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ThemeColors.TEXT_INACTIVE),
                            ],
                        ),
                    ),
                )
            )

        recent_content: ft.Control = ft.Column(
            spacing=8,
            controls=recent_rows,
        )
    else:
        recent_content = ft.Container(
            bgcolor="#F7FAFC",
            border_radius=14,
            padding=12,
            content=ft.Text(
                "No recent food scans yet.",
                size=13,
                color=ThemeColors.TEXT_SECONDARY,
            ),
        )

    recent_scanned_section = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=ThemeColors.CARD_RADIUS_OUTER,
        padding=ThemeColors.CARD_PADDING,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            "Recently Scanned",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ThemeColors.GREEN_TEXT,
                        ),
                        ft.Button(
                            content=ft.Text("Clear", size=12),
                            on_click=on_clear_recent_click,
                            style=ft.ButtonStyle(
                                bgcolor="#F1F4F8",
                                color=ThemeColors.TEXT_PRIMARY,
                                padding=ft.Padding(left=10, top=2, right=10, bottom=2),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                    ],
                ),
                recent_content,
            ],
        ),
    )

    compact_nav = metrics["shell_width"] < 360
    bottom_nav_controls: list[ft.Control] = [
        ft.GestureDetector(
            on_tap=on_home_click,
            content=build_nav_item(ft.Icons.HOME_ROUNDED, "Dashboard", compact=compact_nav),
        ),
        build_nav_item(ft.Icons.CAMERA_ALT_OUTLINED, "Scan Food", selected=True, compact=compact_nav),
        ft.GestureDetector(
            on_tap=on_pantry_click,
            content=build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", compact=compact_nav),
        ),
        ft.GestureDetector(
            on_tap=on_me_click,
            content=build_nav_item(ft.Icons.PERSON_OUTLINE, "Me", compact=compact_nav),
        ),
    ]

    page_controls = cast(list[ft.Control], [
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=26,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, on_click=on_back_click, icon_color="#0F0F0F"),
                    ft.Column(
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                "PantryIQ Connect",
                                size=24 if metrics["is_desktop"] else 18,
                                weight=ft.FontWeight.BOLD,
                                color=ThemeColors.GREEN_TEXT,
                            ),
                            ft.Text(
                                "Scan Food",
                                size=14,
                                color=ThemeColors.TEXT_SECONDARY,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                    ),
                    ft.IconButton(ft.Icons.HELP_OUTLINE_ROUNDED, icon_color="#0F0F0F"),
                ],
            ),
        ),
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Text("📡", size=30),
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(
                                "Scan Product Barcode",
                                size=26 if metrics["is_desktop"] else 20,
                                weight=ft.FontWeight.BOLD,
                                color="#0A1A12",
                            ),
                            ft.Text(
                                "Scan to automatically get shelf life info or enter the product name manually.",
                                size=15,
                                color="#3D4658",
                            ),
                        ],
                    ),
                ],
            ),
        ),
        scanner_surface,
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=action_controls,
        ),
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=14,
            padding=ft.Padding(left=12, top=8, right=12, bottom=8),
            content=ft.Column(
                spacing=4,
                controls=[status_text, result_text],
            ),
        ),
        ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(expand=True, height=1, bgcolor="#C8CED9"),
                ft.Container(
                    bgcolor="#F1F4F8",
                    border_radius=16,
                    padding=ft.Padding(left=16, top=6, right=16, bottom=6),
                    content=ft.Text("OR", size=18, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_SECONDARY),
                ),
                ft.Container(expand=True, height=1, bgcolor="#C8CED9"),
            ],
        ),
        manual_entry_card,
        recent_scanned_section,
        freshness_card,
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=cast(
                list[ft.Control],
                [
                    ft.Button(
                        content=ft.Text("Back"),
                        on_click=on_back_click,
                        style=ft.ButtonStyle(
                            bgcolor="#2E5D4E",
                            color=ThemeColors.BRAND_ON_PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=16),
                        ),
                    ),
                    ft.Button(
                        content=ft.Text("Next"),
                        style=ft.ButtonStyle(
                            bgcolor="#2E5D4E",
                            color=ThemeColors.BRAND_ON_PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=16),
                        ),
                    ),
                ],
            ),
        ),
        # Reserve space for fixed bottom app bar.
        ft.Container(height=74),
    ])

    bottom_nav_bar = ft.Container(
        left=0,
        right=0,
        bottom=0,
        bgcolor="#FFFFFF",
        padding=ft.Padding(left=12, top=8, right=12, bottom=10),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Divider(height=1, color=ThemeColors.DIVIDER),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=bottom_nav_controls,
                ),
            ],
        ),
    )

    container = ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor=ThemeColors.GREEN_SURFACE,
        border_radius=34,
        padding=ft.Padding(left=0, top=0, right=0, bottom=0),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color=ThemeColors.SHELL_SHADOW,
            offset=ft.Offset(0, 8),
        ),
        content=ft.Stack(
            controls=[
                ft.Column(
                    # Page layout order: top navigation, action controls, status lines,
                    # then preview area that hosts camera or fallback message.
                    spacing=ThemeColors.SECTION_SPACING,
                    scroll=ft.ScrollMode.AUTO,
                    controls=page_controls,
                ),
                bottom_nav_bar,
            ],
        ),
    )

    return {
        # Control bundle consumed by BarcodeScannerController for lifecycle,
        # decode updates, and mode-specific button enable/disable behavior.
        "container": container,
        "camera": camera,
        "status_text": status_text,
        "result_text": result_text,
        "capture_button": capture_button,
        "manual_entry_field": manual_entry_field,
        "lookup_overlay": lookup_overlay,
    }
