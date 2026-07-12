# Food-app

Food-app is a simple barcode scanner app built with Flet and OpenCV. It uses your device camera to scan barcodes and display the decoded result.

## Code Tour

Click any link below to jump straight to the matching part of the code in [MAIN.PY](MAIN.PY). This is the fastest way to read the app like a guided tutorial.

- [main() - app setup and UI layout](MAIN.PY#L27)
- [unsharp_mask() - image sharpening helper](MAIN.PY#L59)
- [preprocess_for_pyzbar() - barcode image cleanup](MAIN.PY#L73)
- [process_stream_frame() - live camera barcode scanning](MAIN.PY#L99)
- [capture_photo_and_scan() - photo snapshot scanning](MAIN.PY#L137)
- [start_camera() - camera startup flow](MAIN.PY#L186)
- [stop_camera() - camera shutdown and reset](MAIN.PY#L242)

## Quiz

The line-number quiz has been moved to [BarcodePageQuiz.md](BarcodePageQuiz.md).

## Features

- Start and stop the camera from the app interface
- Scan barcodes using the live camera feed or a captured photo
- Display decoded barcode values in the UI

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Food-app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install the dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Requirements

- Allow camera access when the app prompts for permission.
- A working webcam or camera device is required for scanning.
- The app is intended for desktop environments where Flet and camera support are available.

## Running the app

Start the application with:

```bash
python MAIN.PY
```

If you are using Windows PowerShell, you may need to run:

```powershell
python .\MAIN.PY
```

## Debugging in Visual Studio Code

You can also debug the app directly from Visual Studio Code using a launch configuration.

1. Open the project folder in Visual Studio Code.
2. Press F5 or choose Run and Debug to start the app with the configured launch settings.
3. If prompted, select the Python interpreter for the virtual environment you created earlier.

## Contributing

Please see [Contributing.md](Contributing.md) for contribution guidelines.
