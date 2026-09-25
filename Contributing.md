# Contributing

Thanks for helping improve PantryIQ Connect.

## Branch Workflow

Use one of these long-lived branches as your base:
- `kylee-dev`
- `yaashvi-dev`

Do not develop directly on `main`.

### 1. Pick a base branch and create a feature branch

### 1. Pick a base branch and develop directly on it

Example using `kylee-dev`:

```bash
git checkout kylee-dev
git pull origin kylee-dev
```

Example using `yaashvi-dev`:

```bash
git checkout yaashvi-dev
git pull origin yaashvi-dev
```

Alternate VS Code flow:
1. Open Source Control.
2. Click branch name in the status bar (bottom-left) and switch to `kylee-dev` or `yaashvi-dev`.
3. Open Command Palette and run `Git: Pull`.

### 2. Develop and test locally

Install dependencies if needed:

```bash
python -m pip install -r requirements.txt
```

Run locally:

```bash
python main.py
```

Or web mode:

```bash
flet run --web main.py
```

Alternate VS Code flow:
1. Open Terminal in VS Code and run the same command.
2. Or open Run and Debug and press `F5` to launch with your configured profile.

### 3. Commit and push your branch

```bash
git add .
git commit -m "Describe your change"
git push origin kylee-dev
```

If you are working on `yaashvi-dev`, push with:

```bash
git push origin yaashvi-dev
```

Alternate VS Code flow:
1. Open Source Control.
2. Stage your files (`+` or Stage All).
3. Enter commit message and select Commit.
4. Select Push (or Sync Changes) from Source Control menu.
5. Verify the active branch is `kylee-dev` or `yaashvi-dev` before pushing.

### 4. Create a pull request

Create a PR from your active dev branch into `main`:
- `kylee-dev` -> `main`, or
- `yaashvi-dev` -> `main`

https://github.com/kyleepinto-dot/Food-app/compare/main...kylee-dev

https://github.com/kyleepinto-dot/Food-app/compare/main...yaashvi-dev

In the PR description, include:
- What changed
- Why it changed
- Screenshots (if UI changed)
- Any testing notes

Alternate VS Code flow:
1. Install/sign in to GitHub Pull Requests and Issues extension (if not already).
2. Open Command Palette and run `GitHub Pull Requests: Create Pull Request`.
3. Set base branch to `main`.
4. Set compare branch to `kylee-dev` or `yaashvi-dev`.
5. Fill title/description and create the PR.

### 5. Merge to main

After review and approval, merge the PR into `main`.

Recommended merge order:
1. Commit to `kylee-dev` or `yaashvi-dev`
2. Validate branch changes
3. Open PR to `main` and merge

Alternate VS Code flow:
1. Open the created PR from the Pull Requests view.
2. Confirm checks/reviews are complete.
3. Merge via GitHub UI (recommended) or from PR extension actions.
4. Pull latest `main` locally after merge.

## Sync Regularly with main

Keep your active dev branch up to date with `main` to avoid conflicts.

### Sync a dev branch with main

Example for `kylee-dev`:

```bash
git checkout main
git pull origin main
git checkout kylee-dev
git merge main
git push origin kylee-dev
```

Example for `yaashvi-dev`:

```bash
git checkout main
git pull origin main
git checkout yaashvi-dev
git merge main
git push origin yaashvi-dev
```

Use either `kylee-dev` or `yaashvi-dev` as your working branch and sync it before starting new work.

## Visual Studio Code Guidelines

### Workspace setup

1. Open the repository folder in Visual Studio Code.
2. Select the correct Python interpreter:
	 - Command Palette -> `Python: Select Interpreter`
	 - Prefer the project virtual environment (`.venv`) when available.

### Run and debug

- Run app from terminal:

```bash
python main.py
```

- Run web mode:

```bash
flet run --web main.py
```

- Debug:
	- Press `F5` (Run and Debug).
	- Confirm the selected interpreter is the same one used in terminal runs.

### Code quality checks in VS Code

- Use the Problems panel to resolve Python and import errors before opening a PR.
- Re-run the app after fixes to verify behavior, especially UI/navigation and scanner flow.
- Keep file/module names and imports consistent with current structure:
	- `main.py`
	- `pages/home_page.py`
	- `pages/barcode_page.py`

### Source control in VS Code

- Review changed files in the Source Control view before commit.
- Group related changes in one commit when possible.
- Do not commit temporary/debug-only edits.

## General Guidelines

- Keep PRs focused and easy to review.
- Update docs when behavior or setup changes.
- If you add dependencies, update `requirements.txt`.
- Confirm the app runs before opening or merging a PR.

## Flet App Development Best Practices

- **Organize code by feature**: separate `views`, `services`, `models`, `components`, and `assets`
- **Create reusable UI components**: avoid repeating cards, buttons, chips, and layout code
- **Keep UI and logic separate**: views display data; services handle APIs, storage, and business logic
- **Use routing for multiple screens**: navigate with routes instead of hiding/showing controls
- **Centralize theme colors and styles**: keep branding consistent and easy to update
- **Minimize `page.update()` calls**: update multiple controls first, then refresh once
- **Use async for slow tasks**: API calls, LLM requests, barcode lookup, and database access
- **Use data models**: define clear objects like `FoodResult`, `UserProfile`, or `ScanHistory`
- **Manage app state separately**: don’t store important data only inside UI controls
- **Design mobile-first**: test layouts on phone-sized screens early and often
- **Use Material Design components**: cards, navigation bars, snackbars, dialogs, and bottom sheets
- **Protect secrets**: store API keys in environment variables, not directly in code
- **Use logging instead of print**: easier debugging as the app grows
- **Keep prompts separate**: store LLM prompts in dedicated files for easier updates

### Golden Rule

**Keep screens focused on UI. Put API calls, GPT prompts, storage, and business rules in services.**
