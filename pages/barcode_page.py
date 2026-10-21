import flet as ft
import flet_camera as fc
import flet_permission_handler as fph
import cv2
import numpy as np
import re
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable
from typing import cast
from pyzbar.pyzbar import decode

from pages.theme import ThemeColors


SCAN_WINDOW_LEFT_RATIO = 0.11
SCAN_WINDOW_TOP_RATIO = 0.34
SCAN_WINDOW_WIDTH_RATIO = 0.78
SCAN_WINDOW_HEIGHT_RATIO = 0.38
CAMERA_PREVIEW_ASPECT_RATIO = 4 / 3
SCANNER_VERTICAL_UI_RESERVE = 300
IMAGE_PROCESSING_DEBUG = True
IMAGE_PROCESSING_DEBUG_ROOT = Path("scanner_debug_images")
BARCODE_RECTIFY_HORIZONTAL_MARGIN_RATIO = 0.08
BARCODE_RECTIFY_VERTICAL_MARGIN_RATIO = 0.25
BARCODE_RECTIFIED_RETRY_SCALE = 1.5
PYZBAR_CANDIDATE_NAMES = (
    "grayscale",
    "brightness",
    "clahe",
    "sharpened",
    "thin_bars",
    "balanced_otsu",
    "thick_bars",
)


def get_camera_preview_dimensions(metrics: dict) -> tuple[int, int]:
    width_limit = int(metrics["shell_width"] * (0.9 if metrics["is_desktop"] else 0.92))
    height_limit = max(220, int(metrics["shell_height"]) - SCANNER_VERTICAL_UI_RESERVE)
    width_limited_height = round(width_limit / CAMERA_PREVIEW_ASPECT_RATIO)
    if width_limited_height <= height_limit:
        return width_limit, width_limited_height
    return round(height_limit * CAMERA_PREVIEW_ASPECT_RATIO), height_limit


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
        self.permission_handler = fph.PermissionHandler()
        self.camera = None
        self.running = False
        self.camera_starting = False
        self.camera_generation = 0
        self.streaming_supported = False
        self.status_text = None
        self.result_text = None
        self.camera_action_button = None
        self.capture_button = None
        self.camera_light_button = None
        self.camera_panel = None
        self.scan_container = None
        self.manual_entry_field = None
        self.debug_log_field = None
        self.lookup_overlay = None
        self.on_barcode_detected: Callable[[str], Awaitable[bool]] | None = None
        self.on_product_name_detected: Callable[[str], Awaitable[bool]] | None = None
        self.last_failed_barcode: str | None = None
        self.lookup_in_progress = False
        self.capture_in_progress = False
        self.camera_light_on = False
        self.last_barcode_width_ratio: float | None = None
        self.last_barcode_sharpness: float | None = None
        self.debug_log_lines: list[str] = []
        self.debug_log_path = Path("runtime_debug.log")

    def bind_controls(self, controls: dict):
        # Called after scan UI is built so async handlers can update the
        # visible status/result text and interact with camera/capture controls.
        self.camera_generation += 1
        self.camera = controls["camera"]
        self.status_text = controls["status_text"]
        self.result_text = controls["result_text"]
        self.camera_action_button = controls.get("camera_action_button")
        self.capture_button = controls["capture_button"]
        self.camera_light_button = controls.get("camera_light_button")
        self.camera_panel = controls.get("camera_panel")
        self.scan_container = controls.get("container")
        self.manual_entry_field = controls.get("manual_entry_field")
        self.debug_log_field = controls.get("debug_log_field")
        self.lookup_overlay = controls.get("lookup_overlay")
        self.running = False
        self.camera_starting = False
        self.streaming_supported = False
        self.last_failed_barcode = None
        self.lookup_in_progress = False
        self.capture_in_progress = False
        self.camera_light_on = False
        self.append_debug("bind_controls", "Scan controls bound successfully")

    def resize_view(self, metrics: dict) -> None:
        """Resize mounted scan controls without replacing the active camera."""

        preview_width, preview_height = get_camera_preview_dimensions(metrics)
        if self.camera is not None:
            self.camera.width = preview_width
            self.camera.height = preview_height
        if self.camera_panel is not None:
            self.camera_panel.width = preview_width
            self.camera_panel.height = preview_height
        if self.scan_container is not None:
            self.scan_container.width = metrics["shell_width"]
            self.scan_container.height = metrics["shell_height"]

    def _control_is_mounted(self, control) -> bool:
        """Check attachment without letting Flet's detached-control property raise."""

        if control is None:
            return False
        try:
            return control.page is self.page
        except (AttributeError, RuntimeError):
            return False

    def set_camera_action_state(self, camera_active: bool) -> None:
        # One stable action control changes label and behavior with the camera
        # lifecycle, avoiding separate Start and Stop buttons in the layout.
        if self.camera_action_button is None:
            return
        self.camera_action_button.data = "stop" if camera_active else "start"
        self.camera_action_button.content = ft.Text("Stop Camera" if camera_active else "Start Camera")

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
            lookup_overlay = self.lookup_overlay
            if lookup_overlay is not None and self._control_is_mounted(lookup_overlay):
                lookup_overlay.visible = False
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
            lookup_overlay = self.lookup_overlay
            if lookup_overlay is not None and self._control_is_mounted(lookup_overlay):
                lookup_overlay.visible = False
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

    def image_processing_debug_enabled(self) -> bool:
        platform_name = str(self.page.platform).lower()
        return IMAGE_PROCESSING_DEBUG and "android" not in platform_name

    def create_photo_debug_folder(self) -> Path | None:
        if not self.image_processing_debug_enabled():
            return None

        folder_name = datetime.now().strftime("photo_%Y-%m-%d_%H-%M-%S_%f")
        debug_folder = IMAGE_PROCESSING_DEBUG_ROOT / folder_name
        try:
            debug_folder.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            self.append_debug("image_debug_error", f"Could not create {debug_folder}: {exc}")
            return None
        return debug_folder

    def write_debug_image(self, debug_folder: Path | None, filename: str, image) -> None:
        if debug_folder is None:
            return

        output_path = debug_folder / filename
        try:
            saved = cv2.imwrite(str(output_path), image)
        except cv2.error as exc:
            self.append_debug("image_debug_error", f"Could not write {output_path}: {exc}")
            return
        if not saved:
            self.append_debug("image_debug_error", f"OpenCV did not write {output_path}")

    @staticmethod
    def decoded_barcode_value(barcode) -> str:
        return barcode if isinstance(barcode, str) else barcode.data.decode("utf-8", "ignore")

    def write_decoded_barcode_image(
        self,
        debug_folder: Path | None,
        barcode,
        image,
        decoder_name: str,
    ) -> None:
        barcode_value = self.decoded_barcode_value(barcode)
        safe_barcode = re.sub(r"[^A-Za-z0-9._-]+", "_", barcode_value).strip("._-")
        safe_barcode = safe_barcode[:100] or "unknown"
        self.write_debug_image(
            debug_folder,
            f"decoded_barcode_{safe_barcode}_{decoder_name}_input.png",
            image,
        )

    async def preprocess_for_pyzbar(
        self,
        img,
        debug_folder: Path | None = None,
        debug_prefix: str = "",
        stage_start: int = 2,
    ):
        # Convert to grayscale to reduce dimensionality and stabilize decode.
        grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.write_debug_image(debug_folder, f"{stage_start:02d}_{debug_prefix}grayscale.png", grayscale)

        # Brighten dark captures without washing out already well-lit frames.
        brightness_corrected = grayscale
        mean_luminance = float(np.mean(brightness_corrected))
        if mean_luminance < 120:
            gamma = max(0.55, 0.9 - ((120 - mean_luminance) / 300))
            lookup_table = np.array(
                [((value / 255.0) ** gamma) * 255 for value in range(256)],
                dtype=np.uint8,
            )
            brightness_corrected = cv2.LUT(brightness_corrected, lookup_table)
        self.write_debug_image(
            debug_folder,
            f"{stage_start + 1:02d}_{debug_prefix}brightness_corrected.png",
            brightness_corrected,
        )

        # Local contrast enhancement makes bars readable under uneven light.
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(brightness_corrected)
        self.write_debug_image(
            debug_folder,
            f"{stage_start + 2:02d}_{debug_prefix}local_contrast_clahe.png",
            contrast_enhanced,
        )

        # Apply only light sharpening; strong denoising merged narrow bars in
        # real captures and made otherwise useful candidates less readable.
        sharpened = self.unsharp_mask(
            contrast_enhanced,
            kernel_size=(3, 3),
            sigma=0.8,
            amount=0.65,
        )
        self.write_debug_image(
            debug_folder,
            f"{stage_start + 3:02d}_{debug_prefix}lightly_sharpened.png",
            sharpened,
        )

        # Normalize curved-label lighting before thresholding so shadows do
        # not erase faint bars or make bright bars merge into the background.
        background = cv2.GaussianBlur(brightness_corrected, (0, 0), 15)
        illumination_normalized = cv2.divide(brightness_corrected, background, scale=255)
        self.write_debug_image(
            debug_folder,
            f"{stage_start + 4:02d}_{debug_prefix}illumination_normalized.png",
            illumination_normalized,
        )

        otsu_value, _ = cv2.threshold(
            illumination_normalized,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        threshold_levels = (
            max(0, round(otsu_value) - 15),
            round(otsu_value),
            min(255, round(otsu_value) + 15),
        )
        thresholded_candidates = tuple(
            cv2.threshold(
                illumination_normalized,
                threshold_level,
                255,
                cv2.THRESH_BINARY,
            )[1]
            for threshold_level in threshold_levels
        )
        threshold_names = (
            "low_threshold_thin_bars",
            "balanced_otsu_threshold",
            "high_threshold_thick_bars",
        )
        for index, (threshold_name, thresholded) in enumerate(
            zip(threshold_names, thresholded_candidates)
        ):
            self.write_debug_image(
                debug_folder,
                f"{stage_start + 5 + index:02d}_{debug_prefix}{threshold_name}.png",
                thresholded,
            )

        # Add white border so codes near image edges still have clean margins
        # for pyzbar's detector window.
        padding = 20
        candidates = (
            grayscale,
            brightness_corrected,
            contrast_enhanced,
            sharpened,
            *thresholded_candidates,
        )
        padded_candidates = tuple(
            cv2.copyMakeBorder(
                candidate,
                padding,
                padding,
                padding,
                padding,
                cv2.BORDER_CONSTANT,
                value=255,
            )
            for candidate in candidates
        )
        for index, (candidate_name, candidate) in enumerate(
            zip(PYZBAR_CANDIDATE_NAMES, padded_candidates)
        ):
            self.write_debug_image(
                debug_folder,
                f"{stage_start + 8 + index:02d}_{debug_prefix}{candidate_name}_with_border.png",
                candidate,
            )
        return padded_candidates

    def decode_with_pyzbar(
        self,
        candidates,
        debug_folder: Path | None,
        debug_prefix: str = "",
    ):
        for index, (candidate_name, candidate) in enumerate(
            zip(PYZBAR_CANDIDATE_NAMES, candidates),
            start=1,
        ):
            self.write_debug_image(
                debug_folder,
                f"pyzbar_{debug_prefix}input_{index:02d}_{candidate_name}.png",
                candidate,
            )
            barcodes = decode(candidate)
            if barcodes:
                self.write_decoded_barcode_image(
                    debug_folder,
                    barcodes[0],
                    candidate,
                    f"pyzbar_{debug_prefix.rstrip('_')}" if debug_prefix else "pyzbar",
                )
                return barcodes
        return []

    def decode_candidates_with_opencv(
        self,
        candidates,
        debug_folder: Path | None,
        debug_prefix: str = "",
    ) -> list[str]:
        detector_factory = getattr(cv2, "barcode_BarcodeDetector", None)
        if detector_factory is None:
            self.append_debug("opencv_candidate_error", "OpenCV barcode detector is unavailable")
            return []

        detector = detector_factory()
        for candidate_name, candidate in zip(PYZBAR_CANDIDATE_NAMES, candidates):
            try:
                _, decoded_info, _, _ = detector.detectAndDecodeWithType(candidate)
            except cv2.error as exc:
                self.append_debug(
                    "opencv_candidate_error",
                    f"{candidate_name} decode failed: {exc}",
                )
                continue

            decoded_values = [value for value in decoded_info if value]
            if decoded_values:
                decoder_name = f"opencv_{debug_prefix}{candidate_name}"
                self.write_decoded_barcode_image(
                    debug_folder,
                    decoded_values[0],
                    candidate,
                    decoder_name,
                )
                return decoded_values
        return []

    def detect_and_rectify_barcode(self, scan_region):
        detector_factory = getattr(cv2, "barcode_BarcodeDetector", None)
        if detector_factory is None:
            self.append_debug("barcode_region_error", "OpenCV barcode detector is unavailable")
            return [], None
        detector = detector_factory()
        try:
            _, decoded_info, _, points = detector.detectAndDecodeWithType(scan_region)
        except cv2.error as exc:
            self.append_debug("barcode_region_error", f"OpenCV barcode detection failed: {exc}")
            return [], None

        decoded_values = [value for value in decoded_info if value]
        if points is None or len(points) == 0:
            return decoded_values, None

        quadrilateral = np.asarray(points[0], dtype=np.float32)
        point_sums = quadrilateral.sum(axis=1)
        point_differences = np.diff(quadrilateral, axis=1).reshape(-1)
        ordered = np.array(
            [
                quadrilateral[np.argmin(point_sums)],
                quadrilateral[np.argmin(point_differences)],
                quadrilateral[np.argmax(point_sums)],
                quadrilateral[np.argmax(point_differences)],
            ],
            dtype=np.float32,
        )
        top_left, top_right, bottom_right, bottom_left = ordered
        width = max(
            np.linalg.norm(bottom_right - bottom_left),
            np.linalg.norm(top_right - top_left),
        )
        height = max(
            np.linalg.norm(top_right - bottom_right),
            np.linalg.norm(top_left - bottom_left),
        )
        horizontal_axis = ((top_right - top_left) + (bottom_right - bottom_left)) / 2
        vertical_axis = ((bottom_left - top_left) + (bottom_right - top_right)) / 2
        horizontal_axis /= max(float(np.linalg.norm(horizontal_axis)), 1.0)
        vertical_axis /= max(float(np.linalg.norm(vertical_axis)), 1.0)
        horizontal_margin = width * BARCODE_RECTIFY_HORIZONTAL_MARGIN_RATIO
        vertical_margin = height * BARCODE_RECTIFY_VERTICAL_MARGIN_RATIO
        ordered = np.array(
            [
                top_left - horizontal_axis * horizontal_margin - vertical_axis * vertical_margin,
                top_right + horizontal_axis * horizontal_margin - vertical_axis * vertical_margin,
                bottom_right + horizontal_axis * horizontal_margin + vertical_axis * vertical_margin,
                bottom_left - horizontal_axis * horizontal_margin + vertical_axis * vertical_margin,
            ],
            dtype=np.float32,
        )
        ordered[:, 0] = np.clip(ordered[:, 0], 0, scan_region.shape[1] - 1)
        ordered[:, 1] = np.clip(ordered[:, 1], 0, scan_region.shape[0] - 1)
        output_width = max(1, round(float(width + (2 * horizontal_margin))))
        output_height = max(1, round(float(height + (2 * vertical_margin))))
        destination = np.array(
            [
                [0, 0],
                [output_width - 1, 0],
                [output_width - 1, output_height - 1],
                [0, output_height - 1],
            ],
            dtype=np.float32,
        )
        transform = cv2.getPerspectiveTransform(ordered, destination)
        rectified = cv2.warpPerspective(
            scan_region,
            transform,
            (output_width, output_height),
            borderValue=(255, 255, 255),
        )
        if rectified.shape[0] > rectified.shape[1]:
            rectified = cv2.rotate(rectified, cv2.ROTATE_90_CLOCKWISE)
        self.last_barcode_width_ratio = rectified.shape[1] / scan_region.shape[1]
        rectified_gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
        self.last_barcode_sharpness = float(cv2.Laplacian(rectified_gray, cv2.CV_64F).var())
        return decoded_values, rectified

    def capture_quality_guidance(self) -> str:
        if self.last_barcode_width_ratio is None:
            return "Move the barcode closer and keep it fully inside the scanning box."
        if self.last_barcode_width_ratio < 0.30:
            return "Move closer so the barcode fills more of the scanning box."
        if self.last_barcode_sharpness is not None and self.last_barcode_sharpness < 60:
            return "Hold the package steady and wait for the camera to focus."
        return "Flatten the barcode, reduce the angle, and try again."

    @staticmethod
    def crop_to_scan_window(frame):
        """Return only the pixels shown through the clear scanner guide."""

        frame_height, frame_width = frame.shape[:2]
        left = round(frame_width * SCAN_WINDOW_LEFT_RATIO)
        top = round(frame_height * SCAN_WINDOW_TOP_RATIO)
        right = round(frame_width * (SCAN_WINDOW_LEFT_RATIO + SCAN_WINDOW_WIDTH_RATIO))
        bottom = round(frame_height * (SCAN_WINDOW_TOP_RATIO + SCAN_WINDOW_HEIGHT_RATIO))
        return frame[top:bottom, left:right]

    async def decode_scan_window(self, frame, debug_folder: Path | None = None):
        self.last_barcode_width_ratio = None
        self.last_barcode_sharpness = None
        scan_region = self.crop_to_scan_window(frame)
        if scan_region.size == 0:
            self.append_debug("scan_region", "Clear scanner region did not contain any pixels")
            return []

        self.write_debug_image(debug_folder, "01_scanning_box_crop.png", scan_region)
        candidates = await self.preprocess_for_pyzbar(scan_region, debug_folder)
        barcodes = self.decode_with_pyzbar(candidates, debug_folder)
        if barcodes:
            return barcodes

        decoded_values = self.decode_candidates_with_opencv(candidates, debug_folder)
        if decoded_values:
            return decoded_values

        decoded_values, rectified = self.detect_and_rectify_barcode(scan_region)
        if decoded_values:
            self.write_decoded_barcode_image(
                debug_folder,
                decoded_values[0],
                scan_region,
                "opencv",
            )
            return decoded_values
        if rectified is not None:
            self.write_debug_image(debug_folder, "17_detected_barcode_rectified.png", rectified)
            rectified_candidates = await self.preprocess_for_pyzbar(
                rectified,
                debug_folder,
                debug_prefix="rectified_",
                stage_start=18,
            )
            barcodes = self.decode_with_pyzbar(
                rectified_candidates,
                debug_folder,
                debug_prefix="rectified_",
            )
            if barcodes:
                return barcodes
            upscaled_rectified_candidates = tuple(
                cv2.resize(
                    candidate,
                    None,
                    fx=BARCODE_RECTIFIED_RETRY_SCALE,
                    fy=BARCODE_RECTIFIED_RETRY_SCALE,
                    interpolation=cv2.INTER_CUBIC,
                )
                for candidate in rectified_candidates
            )
            barcodes = self.decode_with_pyzbar(
                upscaled_rectified_candidates,
                debug_folder,
                debug_prefix="rectified_upscaled_",
            )
            if barcodes:
                return barcodes
            decoded_values = self.decode_candidates_with_opencv(
                rectified_candidates,
                debug_folder,
                debug_prefix="rectified_",
            )
            if decoded_values:
                return decoded_values
            decoded_values = self.decode_candidates_with_opencv(
                upscaled_rectified_candidates,
                debug_folder,
                debug_prefix="rectified_upscaled_",
            )
            if decoded_values:
                return decoded_values
        return []

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

        barcodes = await self.decode_scan_window(frame)

        if self.result_text is None:
            return

        if barcodes:
            barcode = barcodes[0]
            barcode_value = self.decoded_barcode_value(barcode)
            self.append_debug("stream_decode", f"Barcode decoded from stream: {barcode_value}")
            await self.handle_decoded_barcode(barcode_value)
        else:
            self.result_text.value = "No barcode scanned yet"

        self.page.update()

    async def capture_photo_and_scan(self, e):
        # The photo handler is shared by the capture button and camera-preview
        # clicks, so both interactions use the same guarded decoding path.
        if not self.running:
            self.append_debug("photo_scan", "Capture requested while camera not running")
            if self.status_text is not None:
                self.status_text.value = "Camera not running"
            if self.result_text is not None:
                self.result_text.value = "Start the camera first, then take a photo"
            self.page.update()
            return

        if self.lookup_in_progress:
            self.append_debug("photo_scan", "Capture ignored while product lookup is in progress")
            return

        if self.capture_in_progress:
            self.append_debug("photo_scan", "Capture ignored while another photo is processing")
            return

        generation = self.camera_generation
        self.capture_in_progress = True
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

            debug_folder = self.create_photo_debug_folder()
            self.write_debug_image(debug_folder, "00_original_camera_frame.png", frame)
            barcodes = await self.decode_scan_window(frame, debug_folder)
            if debug_folder is not None:
                self.append_debug("image_debug", f"Saved photo processing stages to {debug_folder}")

            if barcodes:
                barcode = barcodes[0]
                barcode_value = self.decoded_barcode_value(barcode)
                self.append_debug("photo_scan", f"Barcode decoded from photo: {barcode_value}")
                await self.handle_decoded_barcode(barcode_value)
                if generation != self.camera_generation:
                    return
            elif self.result_text is not None:
                self.append_debug("photo_scan", "No barcode found in captured photo")
                self.result_text.value = self.capture_quality_guidance()

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
        finally:
            if generation == self.camera_generation:
                self.capture_in_progress = False

    async def start_camera(self, e):
        # Guard against duplicate starts from repeated button presses.
        if self.running or self.camera_starting:
            self.append_debug("start_camera", "Start ignored because camera is starting or already running")
            return

        camera = self.camera
        generation = self.camera_generation
        if camera is None or not self._control_is_mounted(camera):
            self.append_debug("start_camera", "Camera control is not mounted on this page")
            self.set_camera_action_state(False)
            if self.status_text is not None:
                self.status_text.value = "Camera preview unavailable"
            if self.result_text is not None:
                self.result_text.value = "Open this app in a supported browser or on Android/iOS to use the camera."
            self.page.update()
            return

        self.camera_starting = True

        if self.status_text is not None:
            self.status_text.value = "Requesting camera access..."
        if self.result_text is not None:
            self.result_text.value = "Opening the camera..."
        self.set_camera_action_state(True)
        self.page.update()

        try:
            # Browser camera access is prompted by the browser. Native mobile
            # apps must obtain the OS runtime permission before camera setup.
            if not bool(getattr(self.page, "web", False)):
                platform_name = str(self.page.platform).lower()
                if "android" in platform_name or "ios" in platform_name:
                    permission_status = await self.permission_handler.request(fph.Permission.CAMERA)
                    self.append_debug("camera_permission", f"Camera permission status={permission_status}")
                    if permission_status != fph.PermissionStatus.GRANTED:
                        if self.status_text is not None:
                            self.status_text.value = "Camera permission denied"
                        if self.result_text is not None:
                            if permission_status == fph.PermissionStatus.PERMANENTLY_DENIED:
                                self.result_text.value = "Enable Camera for PantryIQ Connect in system settings."
                            elif permission_status == fph.PermissionStatus.RESTRICTED:
                                self.result_text.value = "Camera access is restricted by this device."
                            else:
                                self.result_text.value = "Allow camera access to scan a barcode."
                        self.set_camera_action_state(False)
                        self.page.update()
                        return

            if generation != self.camera_generation or not self._control_is_mounted(camera):
                self.append_debug("start_camera", "Camera view changed before device discovery")
                return

            # Prefer the rear camera because it generally has better focus and
            # illumination controls for close-up barcode scanning.
            cameras = await camera.get_available_cameras()
            if generation != self.camera_generation or not self._control_is_mounted(camera):
                self.append_debug("start_camera", "Camera view changed during device discovery")
                return
            if not cameras:
                raise RuntimeError("No camera devices were found")
            self.append_debug("start_camera", f"Detected {len(cameras)} camera device(s)")

            selected_camera = next(
                (
                    available_camera
                    for available_camera in cameras
                    if available_camera.lens_direction == fc.CameraLensDirection.BACK
                ),
                cameras[0],
            )
            await camera.initialize(selected_camera, fc.ResolutionPreset.VERY_HIGH, enable_audio=False)
            if generation != self.camera_generation or not self._control_is_mounted(camera):
                self.append_debug("start_camera", "Camera view changed during initialization")
                return

            try:
                await camera.set_exposure_mode(fc.ExposureMode.AUTO)
                await camera.set_exposure_point(ft.Offset(0.5, 0.5))
                await camera.set_focus_mode(fc.FocusMode.AUTO)
                await camera.set_focus_point(ft.Offset(0.5, 0.5))
                maximum_exposure = await camera.get_max_exposure_offset()
                exposure_offset = max(0.0, min(float(maximum_exposure), 1.5))
                applied_exposure = await camera.set_exposure_offset(exposure_offset)
                self.append_debug("camera_exposure", f"Exposure offset={applied_exposure}")
            except Exception as exc:
                self.append_debug("camera_exposure_error", f"{type(exc).__name__}: {exc}")

            supports_streaming = await camera.supports_image_streaming()
            self.streaming_supported = supports_streaming
            self.append_debug("start_camera", f"Image streaming supported={supports_streaming}")

            if supports_streaming:
                # Best UX: continuous live decoding from incoming frames.
                camera.on_stream_image = self.process_stream_frame
                await camera.start_image_stream()
                if generation != self.camera_generation or not self._control_is_mounted(camera):
                    self.append_debug("start_camera", "Camera view changed while starting image stream")
                    return
                self.running = True
                if self.capture_button is not None:
                    self.capture_button.disabled = True
                if self.camera_light_button is not None:
                    self.camera_light_button.disabled = False
                if self.status_text is not None:
                    self.status_text.value = "Scanning..."
                if self.result_text is not None:
                    self.result_text.value = "Live barcode scanning is active"
            else:
                # Fallback mode: allow manual still-photo capture for decode.
                self.running = True
                if self.capture_button is not None:
                    self.capture_button.disabled = False
                if self.camera_light_button is not None:
                    self.camera_light_button.disabled = False
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
            self.set_camera_action_state(False)
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
        finally:
            if generation == self.camera_generation:
                self.camera_starting = False

    async def toggle_camera_light(self, _e):
        camera = self.camera
        if not self.running or camera is None or not self._control_is_mounted(camera):
            if self.status_text is not None:
                self.status_text.value = "Start the camera before using the light"
            self.page.update()
            return

        requested_state = not self.camera_light_on
        try:
            await camera.set_flash_mode(fc.FlashMode.TORCH if requested_state else fc.FlashMode.OFF)
            self.camera_light_on = requested_state
            if self.camera_light_button is not None:
                self.camera_light_button.content = ft.Text("Light Off" if requested_state else "Light On")
            if self.status_text is not None:
                self.status_text.value = "Camera light on" if requested_state else "Camera light off"
            self.append_debug("camera_light", f"Torch enabled={requested_state}")
        except Exception as exc:
            self.append_debug("camera_light_error", f"{type(exc).__name__}: {exc}")
            if self.status_text is not None:
                self.status_text.value = "Camera light is not supported on this device"
        self.page.update()

    async def _safe_camera_call(self, camera, camera_call, *args):
        # Camera plugin APIs throw when the control is not mounted on page.
        # This guard avoids scheduling calls after the scan view has been
        # replaced (e.g., navigating to product details from manual search).
        if not self._control_is_mounted(camera):
            return

        try:
            await camera_call(*args)
        except Exception as exc:
            self.append_debug("stop_camera_call_error", f"{type(exc).__name__}: {exc}")

    def stop_camera(self):
        # Reset state first so UI and handlers treat camera as inactive.
        self.camera_generation += 1
        self.camera_starting = False
        self.running = False
        self.capture_in_progress = False
        self.camera_light_on = False
        self.set_camera_action_state(False)
        self.append_debug("stop_camera", "Stop requested")

        # Do not queue camera method calls here. Navigation removes the camera
        # control immediately, and late method results for an unmounted control
        # corrupt Flet's invoke-result routing.
        self.streaming_supported = False

        if self.capture_button is not None:
            self.capture_button.disabled = True
        if self.camera_light_button is not None:
            self.camera_light_button.disabled = True
            self.camera_light_button.content = ft.Text("Light On")
        if self.status_text is not None:
            self.status_text.value = "Camera stopped"
        if self.result_text is not None:
            self.result_text.value = "No barcode scanned yet"

    async def stop_camera_and_release(self, _e=None):
        """Stop mounted camera hardware before its control is removed."""

        camera = self.camera
        light_was_on = self.camera_light_on
        streaming_was_supported = self.streaming_supported
        self.stop_camera()

        if camera is not None:
            if light_was_on:
                await self._safe_camera_call(camera, camera.set_flash_mode, fc.FlashMode.OFF)
            if streaming_was_supported:
                await self._safe_camera_call(camera, camera.stop_image_stream)
            await self._safe_camera_call(camera, camera.pause_preview)
            await self._safe_camera_call(camera, camera.set_description, None)


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
    on_toggle_light,
    on_manual_search,
) -> dict:
    # Build the complete scanner shell and return both the root container and
    # individual controls needed by asynchronous camera handlers in main.py.
    status_text = ft.Text(value="Camera ready", size=13, color=ThemeColors.GREEN_TEXT, weight=ft.FontWeight.W_500)
    result_text = ft.Text(
        value="No barcode scanned yet",
        size=16,
        weight=ft.FontWeight.BOLD,
        color="#0A1726",
    )

    camera = fc.Camera(preview_enabled=True, expand=True) if camera_is_supported else None

    def toggle_camera(e):
        clicked_button = cast(ft.Button, e.control)
        if clicked_button.data == "stop":
            on_stop_camera(e)
        else:
            on_start_camera(e)

    camera_action_button = ft.Button(
        content=ft.Text("Start Camera" if camera_is_supported else "Camera unavailable here"),
        data="start",
        on_click=toggle_camera,
        disabled=not camera_is_supported,
        style=ft.ButtonStyle(bgcolor="#2E5D4E", color=ThemeColors.BRAND_ON_PRIMARY),
    )

    if camera_is_supported:
        capture_button = ft.Button(
            content=ft.Text("Take Photo"),
            disabled=True,
            on_click=on_take_photo,
            style=ft.ButtonStyle(
                bgcolor="#FFFFFF",
                color=ThemeColors.TEXT_PRIMARY,
            ),
        )
        camera_light_button = ft.Button(
            content=ft.Text("Light On"),
            disabled=True,
            on_click=on_toggle_light,
            style=ft.ButtonStyle(
                bgcolor="#FFFFFF",
                color=ThemeColors.TEXT_PRIMARY,
            ),
        )
        action_controls: list[ft.Control] = cast(
            list[ft.Control],
            [
                camera_action_button,
                capture_button,
                camera_light_button,
            ],
        )
        preview_content: ft.Control = camera if camera is not None else ft.Container()
    else:
        # Informational fallback for runtimes where camera preview is
        # unsupported, while keeping navigation available.
        capture_button = ft.Button(content=ft.Text("Take Photo"), disabled=True)
        camera_light_button = ft.Button(content=ft.Text("Light On"), disabled=True)
        status_text.value = "Camera preview is unavailable on this platform"
        result_text.value = "This app targets Web, Android, and iOS"
        action_controls = cast(
            list[ft.Control],
            [
                camera_action_button,
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

    preview_frame_width, scanner_surface_height = get_camera_preview_dimensions(metrics)
    if camera is not None:
        camera.expand = False
        camera.width = preview_frame_width
        camera.height = scanner_surface_height
        camera.aspect_ratio = CAMERA_PREVIEW_ASPECT_RATIO
    mask_color = "#33000000"

    # Light translucent panels keep the full camera visible while leaving a
    # centered barcode-shaped opening at normal preview brightness.
    scan_guide_overlay = ft.Column(
        expand=True,
        spacing=0,
        visible=camera_is_supported,
        controls=[
            ft.Container(expand=round(SCAN_WINDOW_TOP_RATIO * 100), bgcolor=mask_color),
            ft.Row(
                expand=round(SCAN_WINDOW_HEIGHT_RATIO * 100),
                spacing=0,
                controls=[
                    ft.Container(expand=round(SCAN_WINDOW_LEFT_RATIO * 100), bgcolor=mask_color),
                    ft.Container(
                        expand=round(SCAN_WINDOW_WIDTH_RATIO * 100),
                        border=ft.Border.all(3, "#FFFFFF"),
                        border_radius=18,
                    ),
                    ft.Container(expand=round(SCAN_WINDOW_LEFT_RATIO * 100), bgcolor=mask_color),
                ],
            ),
            ft.Container(
                expand=round((1 - SCAN_WINDOW_TOP_RATIO - SCAN_WINDOW_HEIGHT_RATIO) * 100),
                bgcolor=mask_color,
            ),
        ],
    )

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

    scanner_surface_content: ft.Control = ft.Stack(
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Stack(
                    controls=[
                        ft.Container(expand=True, content=preview_content),
                        scan_guide_overlay,
                    ],
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
                                "Click or tap the camera to take a photo",
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
    )
    if camera_is_supported:
        scanner_surface_content = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=on_take_photo,
            content=scanner_surface_content,
        )

    camera_panel = ft.Container(
        width=preview_frame_width,
        height=scanner_surface_height,
        border_radius=22,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor="#FFFFFF",
        content=scanner_surface_content,
    )
    scanner_surface = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[camera_panel],
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
        "camera_action_button": camera_action_button,
        "capture_button": capture_button,
        "camera_light_button": camera_light_button,
        "camera_panel": camera_panel,
        "manual_entry_field": manual_entry_field,
        "lookup_overlay": lookup_overlay,
    }
