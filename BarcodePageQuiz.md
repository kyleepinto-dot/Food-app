# Barcode Page Quiz

Use [MAIN.PY](MAIN.PY) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. What does `page.title = "Barcode Scanner"` do?

A. It sets the text shown in the window title bar.

B. It scans the barcode.

C. It opens the camera.

D. It changes the image color.

Your answer:a



2. What does `status_text = ft.Text(value="Camera ready", size=16)` create?

A. A text label that shows the current camera status.

B. A hidden file.

C. A camera device list.

D. A barcode decoder.

Your answer:a



3. What does `camera = fc.Camera(preview_enabled=True, expand=True)` create?

A. The live camera preview control.

B. The barcode result text.

C. The page background.

D. The scan history.

Your answer:a



4. What does `running = False` help the app keep track of?

A. Whether the camera has already been started.

B. Whether the barcode has been read.

C. Whether the file was saved.

D. Whether the photo was rotated.

Your answer:a



5. What does `capture_button = ft.Button(...)` do in the app?

A. It creates the Take Photo button.

B. It opens the camera automatically.

C. It reads the barcode.

D. It turns on the flashlight.

Your answer:a



6. What does `on_click=lambda e: page.run_task(capture_photo_and_scan, e)` do?

A. It runs the photo capture function when the button is clicked.

B. It closes the app.

C. It disables the camera permanently.

D. It changes the title bar.

Your answer:a



7. In `unsharp_mask()`, what is the main purpose of `cv2.GaussianBlur(image, kernel_size, sigma)`?

A. It scans the barcode directly.

B. It creates a blurred version of the image so the code can sharpen edges later.

C. It opens the webcam.

D. It converts the image to text.

Your answer:b



8. In `unsharp_mask()`, why does the code use `np.clip(sharpened, 0, 255)`?

A. To delete blurry pixels.

B. To open the camera.

C. To save the image.

D. To keep pixel values inside the valid image range.

Your answer:d



9. In `preprocess_for_pyzbar()`, what is the main purpose of `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)`?

A. It flips the image.

B. It starts the preview.

C. It converts the image to grayscale.

D. It draws the barcode.

Your answer:c



10. In `preprocess_for_pyzbar()`, what does `cv2.bilateralFilter(...)` help with?

A. It opens the webcam.

B. It reduces noise while keeping edges fairly sharp.

C. It saves the file.

D. It rotates the image.

Your answer:b



11. In `preprocess_for_pyzbar()`, what is the main purpose of `cv2.adaptiveThreshold(...)`?

A. It records camera audio.

B. It resizes the window.

C. It turns the image into a binary black-and-white image so barcode bars stand out more clearly.

D. It saves the image to disk.

Your answer:c



12. In `preprocess_for_pyzbar()`, why does the code add a white border with `cv2.copyMakeBorder(...)`?

A. Many barcodes need a quiet zone around them.

B. To make the camera faster.

C. To close the app.

D. To change the title.

Your answer:a



13. In `process_stream_frame()`, what is `np.frombuffer(image_bytes, np.uint8)` doing?

A. It draws the barcode on the screen.

B. It starts the camera preview.

C. It changes the app theme.

D. It converts raw image bytes into a NumPy array that OpenCV can decode.

Your answer:d



14. In `process_stream_frame()`, why does the code use `cv2.flip(frame, 1)`?

A. To sharpen the barcode.

B. To make the preview behave like a mirror.

C. To open the webcam.

D. To save the frame.

Your answer:b



15. In `process_stream_frame()`, what does `barcodes = decode(gray)` do?

A. It makes the image bigger.

B. It turns the camera on.

C. It asks pyzbar to look for barcodes in the processed image.

D. It clears the screen.

Your answer:c



16. In `capture_photo_and_scan()`, why does the code check `if not running:`?

A. To make sure the camera has already been started before trying to capture a photo.

B. To close the app.

C. To save battery.

D. To rotate the camera preview.

Your answer:a



17. In `capture_photo_and_scan()`, what does `page.update()` do after changing the status text?

A. It saves the photo to disk.

B. It restarts the camera.

C. It deletes the old result text.

D. It refreshes the screen so the user sees the new message right away.

Your answer:d



18. In `start_camera()`, what does `await camera.get_available_cameras()` do?

A. It scans the barcode immediately.

B. It asks the camera control for the list of connected camera devices.

C. It disables the capture button.

D. It turns the image grayscale.

Your answer:b



19. In `start_camera()`, why does the code check `if supports_streaming:`?

A. To change the window size.

B. To delete the camera preview.

C. To decide whether the app should use live barcode scanning or snapshot mode.

D. To close the app.

Your answer:c



20. In `start_camera()`, what does `camera.on_stream_image = process_stream_frame` do?

A. It connects live camera frames to the barcode scanning function.

B. It takes a photo.

C. It changes the app title.

D. It saves the image to disk.

Your answer:a



21. In `start_camera()`, what is `await camera.start_image_stream()` used for?

A. It stops the camera.

B. It clears the preview.

C. It deletes the barcode text.

D. It starts sending camera frames for live scanning.

Your answer:d



22. In `stop_camera()`, what is the purpose of setting `capture_button.disabled = True`?

A. It deletes the button permanently.

B. It prevents photo capture until the camera is started again.

C. It increases image quality.

D. It makes the barcode larger.

Your answer:b



23. In `stop_camera()`, why does the code call `page.run_task(camera.pause_preview)`?

A. To make the barcode brighter.

B. To add a new camera device.

C. To pause the camera preview when scanning stops.

D. To open the photo gallery.

Your answer:c



24. In `stop_camera()`, why does the app reset `status_text.value = "Camera stopped"` and `result_text.value = "No barcode scanned yet"`?

A. To show the user that scanning has ended and the app is idle again.

B. To delete the camera.

C. To change the theme.

D. To save the current photo.

Your answer:a



25. What does `page.on_close = lambda: stop_camera()` help the app do?

A. Take a screenshot.

B. Rotate the camera feed.

C. Increase barcode size.

D. Clean up the camera automatically when the window closes.

Your answer:d



26. What does `result_text.value = "No barcode scanned yet"` help the app communicate?

A. That the camera is broken.

B. That nothing has been detected yet.

C. That the file was deleted.

D. That the barcode was already saved.

Your answer:b



27. Why does `process_stream_frame()` return early when `not image_bytes`?

A. Because the app is done scanning.

B. Because the camera has already stopped forever.

C. Because there is no frame data to process.

D. Because the barcode is too large.

Your answer:c



28. Why does `capture_photo_and_scan()` raise an error if `image_bytes` is empty?

A. Because it cannot scan a photo that was never captured.

B. Because the window is too small.

C. Because the barcode is already decoded.

D. Because the camera preview is hidden.

Your answer:a



29. What is the purpose of `status_text.value = "Scanning..."` in `start_camera()`?

A. It closes the camera.

B. It turns the image grayscale.

C. It saves the result.

D. It tells the user the camera is actively scanning.

Your answer:d



30. What does `page.add(...)` do in the app?

A. It scans the barcode.

B. It places the visible controls on the page.

C. It flips the camera image.

D. It stops the app.

Your answer:b




