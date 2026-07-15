# MAIN.PY Quiz

Use [MAIN.PY](MAIN.PY) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. In `MAIN.PY`, what is the purpose of `view_state = {"current": "home"}`?

A. It stores decoded barcode history.

B. It caches camera frames for performance.

C. It tracks which screen should be rendered (`home` or `scan`).

D. It controls the page background color.

Your answer:



2. In `get_layout_metrics()`, when does the code treat the layout as desktop?

A. When `viewport_w >= 1000`.

B. When `viewport_w >= 430`.

C. When `viewport_h >= 1000`.

D. When `viewport_w < 700`.

Your answer:



3. Why does `render_current_view()` call `page.clean()` before `page.add(...)`?

A. To recompile Python functions.

B. To clear old controls so only the active screen layout is shown.

C. To reset the app window size to defaults.

D. To force camera permissions to re-prompt.

Your answer:



4. What is the role of `page.run_task(scanner_controller.start_camera, e)` in the start callback?

A. It blocks the UI until camera scanning finishes.

B. It runs the async start function without freezing the UI thread.

C. It automatically retries camera startup three times.

D. It converts the callback into a synchronous function.

Your answer:



5. What does `page.on_resized = lambda _: render_current_view()` enable?

A. Automatic camera exposure tuning.

B. Saving resized layouts into a file.

C. Re-rendering the current page so responsive sizes update after window changes.

D. Switching to scan view on every resize.

Your answer:



6. In Python, why is `_` used as the lambda parameter in `lambda _: ...` here?

A. It means the parameter is ignored even though the callback still receives an event object.

B. It creates a global variable shared across modules.

C. It tells Flet to pass no arguments.

D. It converts the callback into an async coroutine.

Your answer:
