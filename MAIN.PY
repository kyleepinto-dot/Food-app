"""
Barcode Scanner App - Quick Tour

Use the function names below as your guide through the file:
- main() -> builds the full app and connects the UI
- start_camera() -> opens the camera and chooses live scan vs photo mode
- process_stream_frame() -> handles each live camera frame
- capture_photo_and_scan() -> takes one snapshot and scans it
- preprocess_for_pyzbar() -> cleans up images before barcode decoding
- stop_camera() -> shuts everything down and resets the screen

Reading order suggestion:
1. Start at main() to see the overall app setup.
2. Read start_camera() to understand how the camera begins.
3. Read preprocess_for_pyzbar() to see how images are prepared.
4. Read process_stream_frame() and capture_photo_and_scan() to see scanning.
5. Finish with stop_camera() to see cleanup.
"""

import flet as ft
import flet_camera as fc
import cv2
import numpy as np
from pyzbar.pyzbar import decode


def main(page: ft.Page):
    # The main function receives the current Flet page and builds the entire app UI on it.
    # Everything the user sees and interacts with is created inside this function.
    page.title = "Barcode Scanner"
    page.window.width = 800
    page.window.height = 700
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    # These labels act like simple status messages.
    # We update them whenever the camera starts, stops, fails, or finds a barcode.
    status_text = ft.Text(value="Camera ready", size=16)
    result_text = ft.Text(value="No barcode scanned yet", size=18, weight=ft.FontWeight.BOLD)

    # This camera control draws the live preview inside the app window.
    camera = fc.Camera(preview_enabled=True, expand=True)

    # running tells us whether the camera was successfully started.
    # streaming_supported tells us whether the platform can send live frames for barcode scanning.
    running = False
    streaming_supported = False

    # This button lets the user capture one still image when live streaming is not available.
    # It starts disabled because the camera is not ready yet.
    capture_button = ft.Button(
        "Take Photo",
        disabled=True,
        on_click=lambda e: page.run_task(capture_photo_and_scan, e),
    )

    # --- Image helpers -----------------------------------------------------
    def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=1.5, threshold=0):
        """Return a sharpened version of the image using unsharp masking."""
        # Blur the image first so we can compare the blurred version to the original.
        blurred = cv2.GaussianBlur(image, kernel_size, sigma)
        # Increase the contrast around edges to make barcode stripes easier to detect.
        sharpened = float(amount + 1) * image - float(amount) * blurred
        # Keep pixel values inside the normal 0-255 image range.
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        if threshold > 0:
            # For very small differences, keep the original pixels unchanged.
            low_contrast_mask = np.absolute(image - blurred) < threshold
            np.copyto(sharpened, image, where=low_contrast_mask)
        return sharpened

    async def preprocess_for_pyzbar(img):
        # pyzbar works best when the image has been simplified before decoding.
        # We convert to grayscale, reduce noise, sharpen edges, and improve contrast.
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Smooth small noise while keeping barcode edges reasonably sharp.
        gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        gray = unsharp_mask(gray)
        
        # Increase contrast so dark and light barcode bars stand out more clearly.
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 15, 3
        )
        
        # Add a white border because many barcodes need empty space around them.
        # That empty space is often called the quiet zone.
        padding = 20
        gray = cv2.copyMakeBorder(
            gray, padding, padding, padding, padding, 
            cv2.BORDER_CONSTANT, value=255
        )
        
        return gray

    # --- Live camera scanning ---------------------------------------------
    async def process_stream_frame(e):
        # This handler is called repeatedly while the camera is streaming.
        # Each call gives us one frame that we can try to decode as a barcode.
        image_bytes = e.bytes
        if not image_bytes:
            return

        try:
            # Convert the raw byte data into an OpenCV image.
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            return

        if frame is None:
            return

        # Flip the image so it behaves more like a mirror preview.
        frame = cv2.flip(frame, 1)

        # Prepare the frame for barcode decoding.
        gray = await preprocess_for_pyzbar(frame)

        # Ask pyzbar to look for barcodes in the processed image.
        barcodes = decode(gray)

        if barcodes:
            # Use the first barcode found and show its decoded text.
            barcode = barcodes[0]
            result_text.value = f"Scanned: {barcode.data.decode('utf-8', 'ignore')}"
        else:
            # If nothing is detected, keep the screen message calm and simple.
            result_text.value = "No barcode scanned yet"

        # Refresh the page so the user sees the updated text immediately.
        page.update()

    # --- Photo capture scanning -------------------------------------------
    async def capture_photo_and_scan(e):
        # This mode captures one still image, then scans that image for a barcode.
        if not running:
            status_text.value = "Camera not running"
            result_text.value = "Start the camera first, then take a photo"
            page.update()
            return

        # Tell the user that the snapshot is in progress.
        status_text.value = "Capturing photo..."
        result_text.value = "Processing image..."
        page.update()

        try:
            # Ask the camera control for a single image.
            image_bytes = await camera.take_picture()
            if not image_bytes:
                raise RuntimeError("No image was captured")

            # Decode the captured bytes into an OpenCV image.
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError("Could not read the captured image")

            # Apply the same cleanup steps that we use for live streaming.
            frame = cv2.flip(frame, 1)
            gray = await preprocess_for_pyzbar(frame)

            # Try to read any barcode from the processed photo.
            barcodes = decode(gray)

            if barcodes:
                # Show the barcode text if one is found.
                barcode = barcodes[0]
                result_text.value = f"Scanned: {barcode.data.decode('utf-8', 'ignore')}"
            else:
                # Let the user know the image was captured but no barcode matched.
                result_text.value = "No barcode found in the photo"

            status_text.value = "Photo captured"
            page.update()
        except Exception as exc:
            # Any unexpected failure gets shown as a friendly message.
            status_text.value = f"Photo error: {exc}"
            result_text.value = "Could not read the captured photo"
            page.update()

    # --- Camera lifecycle --------------------------------------------------
    async def start_camera(e):
        # Start-up flow:
        # 1. Ask for available cameras.
        # 2. Initialize the first camera.
        # 3. Choose live streaming if the platform supports it.
        nonlocal running, streaming_supported

        if running:
            # If the camera is already running, there is nothing else to do.
            return

        # Update the UI before doing any slow camera work.
        status_text.value = "Requesting camera access..."
        result_text.value = "Opening the camera..."
        page.update()

        try:
            # Get the list of connected camera devices.
            cameras = await camera.get_available_cameras()
            if not cameras:
                raise RuntimeError("No camera devices were found")

            # Initialize the first camera at a medium quality level.
            await camera.initialize(cameras[0], fc.ResolutionPreset.MEDIUM, enable_audio=False)

            # Check whether the current platform can deliver frames continuously.
            supports_streaming = await camera.supports_image_streaming()
            streaming_supported = supports_streaming
            if supports_streaming:
                # In streaming mode, each frame is sent to process_stream_frame.
                camera.on_stream_image = process_stream_frame
                await camera.start_image_stream()
                running = True
                capture_button.disabled = True
                status_text.value = "Scanning..."
                result_text.value = "Live barcode scanning is active"
            else:
                # If streaming is not supported, we still keep the camera open for snapshots.
                running = True
                capture_button.disabled = False
                status_text.value = "Camera preview ready"
                result_text.value = (
                    "Live barcode scanning is not available on this platform. "
                    "Use Take Photo when ready."
                )

            page.update()
        except Exception as exc:
            # Show a readable message if the camera cannot be started.
            running = False
            status_text.value = f"Camera error: {exc}"
            result_text.value = (
                "Please allow camera access and make sure a webcam is connected."
            )
            page.update()

    def stop_camera():
        # Stop any active camera work and reset the screen back to the idle state.
        nonlocal running, streaming_supported
        running = False
        try:
            if camera is not None and streaming_supported:
                # Stop the live frame stream if we previously started it.
                page.run_task(camera.stop_image_stream)
        except Exception:
            pass
        try:
            if camera is not None:
                # Pause the preview so the camera is no longer active in the UI.
                page.run_task(camera.pause_preview)
        except Exception:
            pass
        try:
            if camera is not None:
                # Clear the camera description so the control returns to a clean state.
                page.run_task(camera.set_description, None)
        except Exception:
            pass
        capture_button.disabled = True
        streaming_supported = False
        status_text.value = "Camera stopped"
        result_text.value = "No barcode scanned yet"
        page.update()

    # --- UI setup ----------------------------------------------------------
    # Build the visible interface:
    # - a short instruction at the top
    # - control buttons
    # - status messages
    # - the camera preview area
    page.add(
        ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # This text tells the user what to point the camera at.
                ft.Text("Point the camera at a barcode", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        # Start Camera asks the app to open the webcam.
                        ft.Button("Start Camera", on_click=lambda e: page.run_task(start_camera, e)),
                        # Stop Camera turns everything off and resets the interface.
                        ft.Button("Stop Camera", on_click=lambda _: stop_camera()),
                        # Take Photo is used when live scanning is not available.
                        capture_button,
                    ],
                ),
                # Show the current camera state.
                status_text,
                # Show the latest barcode result or a friendly fallback message.
                result_text,
                # Keep the preview area a fixed size so the layout stays stable.
                ft.Container(
                    width=640,
                    height=480,
                    bgcolor=ft.Colors.BLACK,
                    content=camera,
                ),
            ],
        )
    )

    # Make sure we clean up the camera when the app window closes.
    page.on_close = lambda: stop_camera()


ft.run(main)
