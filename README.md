# PantryIQ Connect

PantryIQ Connect is a Flet-based barcode scanning app.

It includes:
- A Home dashboard UI
- A Barcode scan screen
- Responsive layout behavior for mobile, tablet, and desktop web sizes
- Camera-based scanning on supported targets

## Project Structure

- `main.py`
  - App entrypoint
  - Screen navigation and rendering
  - Responsive layout metrics
  - Wires callbacks between pages and scanner controller
- `pages/home_page.py`
  - Home screen UI components and layout
- `pages/barcode_page.py`
  - Barcode screen UI components and layout
  - `BarcodeScannerController` for camera lifecycle and barcode decoding
- `pages/theme.py`
  - Centralized `ThemeColors` tokens shared across UI pages
- `MainPageQuiz.cmd`
  - Multiple-choice learning quiz focused on `main.py`
- `pages/HomePageQuiz.md`
  - Multiple-choice learning quiz focused on `home_page.py`
- `pages/BarcodePageQuiz.md`
  - Multiple-choice learning quiz focused on `barcode_page.py`

## Code Tour

- [App bootstrap and flow](main.py)
- [Home page UI](pages/home_page.py)
- [Barcode page UI](pages/barcode_page.py)
- [Theme color tokens](pages/theme.py)

## Quiz

- [Main page quiz](MainPageQuiz.cmd)
- [Home page quiz](pages/HomePageQuiz.md)
- [Barcode page quiz](pages/BarcodePageQuiz.md)

## Features

- Home page with:
  - Scan Food CTA button
  - Goal Tracker card
  - Monthly summary cards
- Barcode page with:
  - Start Camera
  - Stop Camera
  - Take Photo (when streaming fallback applies)
  - Live barcode decoding result display
- Centralized theme tokens:
  - Shared color constants in `pages/theme.py`
  - Consistent styling across app screens

## Platform Notes

The app is designed for Web, Android, and iOS camera experiences.

If camera access fails in browser mode, verify:
- Camera permission is allowed in browser site settings
- You are running in a secure context (`localhost` or `https`)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd PantryIQ\ Connect
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

Run the app:

```bash
python main.py
```

For web mode:

```bash
flet run --web main.py
```

## AI Meal Images

Pollinations currently requires authenticated credit for new AI image
generations. Without a token, the app automatically uses a relevant meal photo
for each dish. For local or debug runs that require generated AI images, provide
a token through the environment before starting the app:

```powershell
$env:POLLINATIONS_API_KEY="your-token"
python main.py
```

Do not commit the token or embed it in an Android/iOS build. Production mobile
builds should call an authenticated backend proxy. Meal suggestions and any
successfully downloaded images are cached in the local `pantry.db` and reused
while the signed-in user's pantry signature remains unchanged.

## Debugging in Visual Studio Code

1. Open the project folder in Visual Studio Code.
2. Press `F5` or choose Run and Debug.
3. Select your Python interpreter if prompted.

## Contributing

Please see [Contributing.md](Contributing.md) for contribution guidelines.
