import flet as ft
import flet_camera as fc
import cv2
import numpy as np
from pyzbar.pyzbar import decode


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

    def bind_controls(self, controls: dict):
        # Called after scan UI is built so handlers can update controls.
        self.camera = controls["camera"]
        self.status_text = controls["status_text"]
        self.result_text = controls["result_text"]
        self.capture_button = controls["capture_button"]
        self.running = False
        self.streaming_supported = False

    def camera_supported_on_platform(self) -> bool:
        if bool(getattr(self.page, "web", False)):
            return True

        platform_name = str(self.page.platform).lower()
        return "android" in platform_name or "ios" in platform_name

    @staticmethod
    def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=1.5, threshold=0):
        blurred = cv2.GaussianBlur(image, kernel_size, sigma)
        sharpened = float(amount + 1) * image - float(amount) * blurred
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        if threshold > 0:
            low_contrast_mask = np.absolute(image - blurred) < threshold
            np.copyto(sharpened, image, where=low_contrast_mask)
        return sharpened

    async def preprocess_for_pyzbar(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        gray = self.unsharp_mask(gray)
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,
            3,
        )

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
        image_bytes = e.bytes
        if not image_bytes:
            return

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            return

        if frame is None:
            return

        frame = cv2.flip(frame, 1)
        gray = await self.preprocess_for_pyzbar(frame)
        barcodes = decode(gray)

        if self.result_text is None:
            return

        if barcodes:
            barcode = barcodes[0]
            self.result_text.value = f"Scanned: {barcode.data.decode('utf-8', 'ignore')}"
        else:
            self.result_text.value = "No barcode scanned yet"

        self.page.update()

    async def capture_photo_and_scan(self, e):
        if not self.running:
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
                self.result_text.value = f"Scanned: {barcode.data.decode('utf-8', 'ignore')}"
            else:
                self.result_text.value = "No barcode found in the photo"

            self.status_text.value = "Photo captured"
            self.page.update()
        except Exception as exc:
            self.status_text.value = f"Photo error: {exc}"
            self.result_text.value = "Could not read the captured photo"
            self.page.update()

    async def start_camera(self, e):
        if self.running:
            return

        if self.status_text is not None:
            self.status_text.value = "Requesting camera access..."
        if self.result_text is not None:
            self.result_text.value = "Opening the camera..."
        self.page.update()

        if self.camera is None:
            return

        try:
            cameras = await self.camera.get_available_cameras()
            if not cameras:
                raise RuntimeError("No camera devices were found")

            await self.camera.initialize(cameras[0], fc.ResolutionPreset.MEDIUM, enable_audio=False)

            supports_streaming = await self.camera.supports_image_streaming()
            self.streaming_supported = supports_streaming

            if supports_streaming:
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

    def stop_camera(self):
        self.running = False

        if self.camera is not None:
            try:
                if self.streaming_supported:
                    self.page.run_task(self.camera.stop_image_stream)
            except Exception:
                pass

            try:
                self.page.run_task(self.camera.pause_preview)
            except Exception:
                pass

            try:
                self.page.run_task(self.camera.set_description, None)
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
    on_back_click,
    on_start_camera,
    on_stop_camera,
    on_take_photo,
) -> dict:
    # Build scanner page UI and return both the container and key controls.
    # MAIN.PY stores these controls to update status/result from async handlers.
    status_text = ft.Text(value="Camera ready", size=15, color="#303030")
    result_text = ft.Text(
        value="No barcode scanned yet",
        size=17,
        weight=ft.FontWeight.BOLD,
        color="#111111",
    )

    camera = fc.Camera(preview_enabled=True, expand=True) if camera_is_supported else None

    if camera_is_supported:
        # Full scanning controls for supported targets (web, Android, iOS).
        capture_button = ft.Button(
            "Take Photo",
            disabled=True,
            on_click=on_take_photo,
        )
        action_controls = [
            ft.Button(
                "Start Camera",
                on_click=on_start_camera,
                style=ft.ButtonStyle(bgcolor="#1AA87C", color="#FFFFFF"),
            ),
            ft.Button(
                "Stop Camera",
                on_click=on_stop_camera,
            ),
            capture_button,
        ]
        preview_area = ft.Container(
            width=None,
            expand=True,
            height=metrics["camera_height"],
            border_radius=10,
            bgcolor="#111111",
            content=camera,
        )
    else:
        # Informational fallback for runtimes where camera preview is unavailable.
        capture_button = ft.Button("Take Photo", disabled=True)
        status_text.value = "Camera preview is unavailable on this platform"
        result_text.value = "This app targets Web, Android, and iOS"
        action_controls = [
            ft.Button(
                "Back Home",
                on_click=on_back_click,
            )
        ]
        preview_area = ft.Container(
            width=None,
            expand=True,
            height=metrics["camera_height"],
            border_radius=10,
            bgcolor="#F2F4F5",
            alignment=ft.Alignment(0, 0),
            content=ft.Text(
                "Camera preview is supported on Web, Android, and iOS.",
                color="#333333",
                size=16,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    container = ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor="#FFFFFF",
        border_radius=34,
        padding=ft.Padding(left=16, top=16, right=16, bottom=16),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color="#22000000",
            offset=ft.Offset(0, 8),
        ),
        content=ft.Column(
            # Page structure: top bar, action row, status output, preview area.
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_ROUNDED,
                            on_click=on_back_click,
                        ),
                        ft.Text(
                            "Barcode Scan",
                            size=28 if metrics["is_desktop"] else 24,
                            weight=ft.FontWeight.BOLD,
                            color="#111111",
                        ),
                        ft.Container(width=40),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=action_controls,
                ),
                status_text,
                result_text,
                preview_area,
            ],
        ),
    )

    return {
        # Return the control bundle so main logic can manage camera state.
        "container": container,
        "camera": camera,
        "status_text": status_text,
        "result_text": result_text,
        "capture_button": capture_button,
    }
