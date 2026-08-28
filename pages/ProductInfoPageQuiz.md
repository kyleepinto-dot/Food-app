# product_info_page.py Quiz

Use [product_info_page.py](product_info_page.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. What is the main job of `_normalize_fattom_level(value, default)`?

A. Convert icons to Unicode.

B. Normalize text to one of `High`, `Medium`, or `Low`, else use default.

C. Resize image cards.

D. Build bottom navigation rows.

Your answer: b


2. In `_derive_default_fattom_from_text()`, why are keywords like `milk`, `fish`, and `meat` checked?

A. To choose default FATTOM levels based on food type risk clues.

B. To fetch ingredient lists online.

C. To reorder image gallery slides.

D. To detect screen orientation.

Your answer: a


3. In `_extract_fattom_levels()`, what happens when `ai_profile["fattom"]` is not a dict?

A. The function raises an exception.

B. It ignores FATTOM and returns empty fields.

C. It falls back to flat keys like `fattom_food`, `fattom_time`, etc.

D. It always sets every level to `High`.

Your answer: c


4. In `_derive_food_profile()`, when does the function return source `"AI"`?

A. Whenever `product_name` exists.

B. Only when required AI fields are present and non-empty.

C. Only for frozen products.

D. Never; it always returns fallback.

Your answer: b


5. What does `_derive_product_handling_tips()` produce?

A. Camera calibration values.

B. Ethylene guidance and waste-reduction tips based on product text.

C. QR decoding results.

D. Theme token overrides.

Your answer: b


6. In `_fattom_grid()`, how does layout differ on desktop vs mobile?

A. Desktop uses 3 cards per row; mobile uses 2.

B. Desktop hides oxygen/moisture cards.

C. Mobile uses 6 cards per row.

D. Both always use 1 card per row.

Your answer: a


7. In image gallery setup, what does `show_ai_first` influence?

A. Whether quantity field is visible.

B. The initial image index so AI image can be shown first when available.

C. The product risk level.

D. The bottom nav selection.

Your answer: b


8. In `on_swipe_end(e)`, what triggers moving to the next image?

A. `primary_velocity < -20`

B. `primary_velocity == 0`

C. `primary_velocity > 200`

D. Any tap on the image.

Your answer: c


9. What does `quantity_field` capture for `on_add_to_pantry`?

A. Image source preference.

B. Quantity to add to pantry.

C. Barcode checksum.

D. Theme selection.

Your answer: b


10. Why is there a final spacer `ft.Container(height=160)` in `content_controls`?

A. To improve AI confidence.

B. To reserve scroll space so floating add button does not hide final cards.

C. To lock card heights.

D. To hide summary text.

Your answer: b
