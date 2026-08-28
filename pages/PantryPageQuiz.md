# pantry_page.py Quiz

Use [pantry_page.py](pantry_page.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. In `build_pantry_shell()`, what does this expression do?

`pantry_items = [item for item in pantry_products if isinstance(item, dict)]`

A. It converts all items to strings.

B. It keeps only valid dictionary pantry entries.

C. It removes items with quantity 1.

D. It sorts items alphabetically.

Your answer: b


2. How is `pantry_item_count` calculated?

A. By counting only unique categories.

B. By summing the `quantity` value across pantry items.

C. By reading a fixed number from settings.

D. By counting the number of icons displayed.

Your answer: b


3. In `_pantry_item()`, what do the add/remove icon buttons do?

A. Open product details.

B. Trigger `on_quantity_change(item_key, +/-1)` to adjust quantity.

C. Delete the entire pantry.

D. Start camera scanning.

Your answer: b


4. What UI is shown when `pantry_items` is empty?

A. A crash message from Python.

B. A text prompt telling users to add a scanned product.

C. A hidden blank page with no controls.

D. A camera preview fallback.

Your answer: b

5. Which bottom nav item is marked selected in this page?

A. Dashboard

B. Scan Food

C. Pantry

D. Me

Your answer: c


6. What is the purpose of the badge text like `f"{pantry_item_count} Items"` in the hero section?

A. To show the current total number of pantry items.

B. To display refrigerator temperature.

C. To list all categories in one label.

D. To show network status.

Your answer: a


7. In the "Storage Snapshot" row, which value is dynamic from app state?

A. Fridge count only.

B. Freezer count only.

C. Pantry count, via `pantry_item_count`.

D. All three are fetched from API.

Your answer: c


8. Why is `ft.Container(height=74)` added near the end of `content_controls`?

A. To leave room so bottom controls are not obscured by the nav bar.

B. To enable AI image generation.

C. To animate item quantity updates.

D. To force tablet layout.

Your answer: a
