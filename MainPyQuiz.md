# MAIN.PY Quiz

Use [MAIN.PY](MAIN.PY) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. What is the primary role of `main(page: ft.Page)`?

A. Decode barcode bytes directly.

B. Configure app state, navigation, and render screen shells.

C. Train an AI model for food recognition.

D. Store products in a remote database.

Your answer:b


2. Why is `view_state` stored as a dictionary?

A. So nested callback functions can mutate shared state without using many globals/nonlocal variables.

B. To enforce read-only state.

C. To serialize UI controls into JSON.

D. To avoid using Flet callbacks.

Your answer:a


3. What does `remember_recent_product(product)` do?

A. Adds product to recent history with deduplication and keeps a short list.

B. Clears all pantry items.

C. Sends product to Open Food Facts.

D. Stops the camera stream.

Your answer:a


4. In `add_product_to_pantry(quantity_value=1)`, why is `max(1, int(...))` used?

A. To limit quantities to zero.

B. To ensure at least quantity 1 is added.

C. To round to nearest ten.

D. To convert quantity into category text.

Your answer:b


5. What is the purpose of `warm_image_url(url)`?

A. Preload a small chunk to trigger image generation readiness before display.

B. Resize images to 64x64.

C. Convert AI image to base64.

D. Cache all image bytes permanently.

Your answer:a


6. In `hydrate_ai_food_profile_async(product)`, what happens on cache hit?

A. It skips profile assignment and returns `None`.

B. It applies cached profile, sets status, and can rerender visible product page.

C. It deletes old cached profile first.

D. It restarts the camera.

Your answer:b


7. Why does `render_current_view()` call `scanner_controller.stop_camera()` when leaving scan mode?

A. To increase font size.

B. To release camera/stream resources before switching screens.

C. To clear pantry quantities.

D. To force desktop layout.

Your answer:b


8. What does `page.on_resize = lambda _: render_current_view()` provide?

A. Immediate rerender on window resize so responsive metrics are reapplied.

B. Disables touch input on tablets.

C. Clears AI cache when window changes.

D. Runs barcode lookup automatically.

Your answer:a


9. In `on_barcode_detected(barcode)`, why are `page.run_task(...)` calls used after initial render?

A. To block UI until all AI enrichment is complete.

B. To run AI image/profile hydration asynchronously without freezing UI.

C. To avoid setting product state.

D. To force fallback profile usage.

Your answer:b


10. What is the practical effect of centralizing navigation via `show_home/show_scan/show_pantry/show_me`?

A. It isolates route logic and keeps screen switches consistent through one renderer.

B. It disables back navigation.

C. It removes need for callbacks.

D. It makes all pages static.

Your answer:a
