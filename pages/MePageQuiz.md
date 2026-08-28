# me_page.py Quiz

Use [me_page.py](me_page.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. In `build_nav_item()`, what happens when `compact=True`?

A. The icon size becomes zero.

B. The label text is omitted and spacing is reduced.

C. The item becomes non-clickable.

D. The selected color changes to red.

Your answer:b


2. What is the purpose of `_profile_metric(label, value)`?

A. To fetch profile data from a server.

B. To build a small metric card showing a label and value.

C. To open the settings page.

D. To validate user input.

Your answer:b


3. In `_setting_row()`, why is `ft.MainAxisAlignment.SPACE_BETWEEN` used?

A. To keep the row hidden.

B. To place the label group on the left and chevron on the right.

C. To stack all controls vertically.

D. To animate the row when tapped.

Your answer:b


4. What does this line do in `build_me_shell()`?

`profile_name = str(profile.get("name") or "PantryIQ Member")`

A. Ensures a default profile name is used when missing.

B. Forces all users to be renamed.

C. Reads a value from local storage only.

D. Converts a number to a random name.

Your answer:a


5. Why does the code compute `compact_nav = metrics["shell_width"] < 360`?

A. To switch navigation to a compact layout on narrow shells.

B. To disable the profile page on desktop.

C. To increase camera height.

D. To hide all icons.

Your answer:a


6. What is the role of `ft.GestureDetector(on_tap=...)` around nav items?

A. It adds hover-only behavior for desktop.

B. It prevents icon rendering.

C. It makes nav items tappable and wires navigation callbacks.

D. It compresses the bottom bar height.

Your answer:c


7. Why is `bottom_nav_bar` placed together with content inside an `ft.Stack`?

A. To overlay/fix the bottom navigation while content can scroll underneath.

B. To merge all controls into one text field.

C. To avoid using colors in the page.

D. To center only the profile avatar.

Your answer:a


8. What is the purpose of the final `ft.Container(height=74)` in `content_controls`?

A. To reserve bottom scroll space so content is not hidden behind the nav bar.

B. To draw a horizontal divider.

C. To store profile metrics in memory.

D. To reset all settings rows.

Your answer:a
