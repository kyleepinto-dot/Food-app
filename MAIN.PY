import flet as ft
import flet_camera as fc
import cv2
import numpy as np
from pyzbar.pyzbar import decode


def main(page: ft.Page):
    page.title = "Barcode Scanner"
    page.window.width = 800
    page.window.height = 700
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    status_text = ft.Text(value="Camera ready", size=16)
    result_text = ft.Text(value="No barcode scanned yet", size=18, weight=ft.FontWeight.BOLD)

    camera = fc.Camera(preview_enabled=True, expand=True)
    running = False
    streaming_supported = False
    capture_button = ft.Button(
        "Take Photo",
        disabled=True,
        on_click=lambda e: page.run_task(capture_photo_and_scan, e),
    )

    def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=1.5, threshold=0):
        """Return a sharpened version of the image using unsharp masking."""
        blurred = cv2.GaussianBlur(image, kernel_size, sigma)
        sharpened = float(amount + 1) * image - float(amount) * blurred
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        if threshold > 0:
            low_contrast_mask = np.absolute(image - blurred) < threshold
            np.copyto(sharpened, image, where=low_contrast_mask)
        return sharpened

    async def preprocess_for_pyzbar(img):  
        # 2. Extract best channel (or default to grayscale if purely B&W)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 3. Clean up noise while keeping edges sharp
        gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        gray = unsharp_mask(gray)
        
        # 4. Handle uneven lighting/glare
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 15, 3
        )
        
        # 5. Add a synthetic white border (Guarantees the required "Quiet Zone")
        padding = 20
        gray = cv2.copyMakeBorder(
            gray, padding, padding, padding, padding, 
            cv2.BORDER_CONSTANT, value=255
        )
        
        return gray

    async def process_stream_frame(e):

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
        gray = await preprocess_for_pyzbar(frame)
        barcodes = decode(gray)

        if barcodes:
            barcode = barcodes[0]
            result_text.value = f"Scanned: {barcode.data.decode('utf-8', 'ignore')}"
        else:
            result_text.value = "No barcode scanned yet"

        page.update()

    async def capture_photo_and_scan(e):
        if not running:
            status_text.value = "Camera not running"
            result_text.value = "Start the camera first, then take a photo"
            page.update()
            return

        status_text.value = "Capturing photo..."
        result_text.value = "Processing image..."
        page.update()

        try:
            image_bytes = await camera.take_picture()
            if not image_bytes:
                raise RuntimeError("No image was captured")

            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError("Could not read the captured image")

            frame = cv2.flip(frame, 1)
            gray = await preprocess_for_pyzbar(frame)
            barcodes = decode(gray)

            if barcodes:
                barcode = barcodes[0]
                result_text.value = f"Scanned: {barcode.data.decode('utf-8', 'ignore')}"
            else:
                result_text.value = "No barcode found in the photo"

            status_text.value = "Photo captured"
            page.update()
        except Exception as exc:
            status_text.value = f"Photo error: {exc}"
            result_text.value = "Could not read the captured photo"
            page.update()

    async def start_camera(e):
        nonlocal running, streaming_supported

        if running:
            return

        status_text.value = "Requesting camera access..."
        result_text.value = "Opening the camera..."
        page.update()

        try:
            cameras = await camera.get_available_cameras()
            if not cameras:
                raise RuntimeError("No camera devices were found")

            await camera.initialize(cameras[0], fc.ResolutionPreset.MEDIUM, enable_audio=False)

            supports_streaming = await camera.supports_image_streaming()
            streaming_supported = supports_streaming
            if supports_streaming:
                camera.on_stream_image = process_stream_frame
                await camera.start_image_stream()
                running = True
                capture_button.disabled = True
                status_text.value = "Scanning..."
                result_text.value = "Live barcode scanning is active"
            else:
                running = True
                capture_button.disabled = False
                status_text.value = "Camera preview ready"
                result_text.value = (
                    "Live barcode scanning is not available on this platform. "
                    "Use Take Photo when ready."
                )

            page.update()
        except Exception as exc:
            running = False
            status_text.value = f"Camera error: {exc}"
            result_text.value = (
                "Please allow camera access and make sure a webcam is connected."
            )
            page.update()

    def stop_camera():
        nonlocal running, streaming_supported
        running = False
        try:
            if camera is not None and streaming_supported:
                page.run_task(camera.stop_image_stream)
        except Exception:
            pass
        try:
            if camera is not None:
                page.run_task(camera.pause_preview)
        except Exception:
            pass
        try:
            if camera is not None:
                page.run_task(camera.set_description, None)
        except Exception:
            pass
        capture_button.disabled = True
        streaming_supported = False
        status_text.value = "Camera stopped"
        result_text.value = "No barcode scanned yet"
        page.update()

    page.add(
        ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Point the camera at a barcode", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Button("Start Camera", on_click=lambda e: page.run_task(start_camera, e)),
                        ft.Button("Stop Camera", on_click=lambda _: stop_camera()),
                        capture_button,
                    ],
                ),
                status_text,
                result_text,
                ft.Container(
                    width=640,
                    height=480,
                    bgcolor=ft.Colors.BLACK,
                    content=camera,
                ),
            ],
        )
    )

    page.on_close = lambda: stop_camera()


ft.run(main)
