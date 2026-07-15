# home_page.py Quiz

Use [home_page.py](home_page.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. In `build_stat_card()`, what does `expand=True` on the outer `ft.Container` help with?

A. It makes the container use available horizontal space in its parent layout.

B. It forces the card to be exactly 12 pixels wide.

C. It prevents text from rendering inside the card.

D. It enables automatic dark mode.

Your answer:



2. In `build_nav_item()`, what changes when `selected=True`?

A. The icon is removed and replaced by plain text.

B. The item becomes disabled and non-clickable.

C. Icon/text colors switch to brand color and text weight becomes bold.

D. The app navigates immediately to scan view.

Your answer:



3. Why is `content_padding` computed with `24 if metrics["is_desktop"] else 18`?

A. To apply slightly larger spacing on desktop for better proportional layout.

B. To sync camera frame rate with CPU speed.

C. To avoid calling `ft.Padding` in Python.

D. To keep button heights always at 54.

Your answer:



4. What does this line indicate in Flet: `shape=ft.RoundedRectangleBorder(radius=27)`?

A. The button corners are rounded with a 27px radius.

B. The button border thickness is fixed at 27.

C. The button text size is 27.

D. The button is clipped to a circle.

Your answer:



5. In the goal tracker, what does `value=0.64` in `ft.ProgressBar(...)` represent?

A. 0.64 pixels of progress.

B. 64% completion.

C. 6.4% completion.

D. 64 completed goals.

Your answer:



6. Why is `ft.Container(expand=True)` placed before the divider and bottom navigation?

A. It acts as a flexible spacer that pushes lower controls toward the bottom.

B. It loads icons lazily for better startup speed.

C. It groups all navigation buttons into one control.

D. It reduces the shell border radius dynamically.

Your answer:



7. What is the purpose of wrapping the Scan nav item with `ft.GestureDetector(on_tap=on_scan_click, ...)`?

A. To apply progress animation on the nav icon.

B. To intercept only keyboard input events.

C. To make that nav item tappable and trigger scan navigation.

D. To disable touches on mobile devices.

Your answer:



8. In the header row, what does `alignment=ft.MainAxisAlignment.SPACE_BETWEEN` do?

A. It stacks controls vertically.

B. It places controls with maximum space between them across the row.

C. It centers all controls into one position.

D. It makes each control the same width automatically.

Your answer:



9. What does the type hint `def build_home_shell(...) -> ft.Container:` communicate?

A. The function must run asynchronously.

B. The function returns a `ft.Container` object.

C. The function takes only container inputs.

D. The function can return any JSON-like dictionary.

Your answer:



10. Why does the code use a shared `ThemeColors` class instead of inline hex colors everywhere?

A. To avoid importing `flet` in the page file.

B. To centralize styling and make color updates easier and more consistent.

C. To force all controls to have identical sizes.

D. To remove the need for `page.update()`.

Your answer:
