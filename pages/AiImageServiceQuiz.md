# ai_image_service.py Quiz

Use [ai_image_service.py](ai_image_service.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. What does `build_ai_food_image_url(food_name, barcode=None)` return when `food_name` is empty?

A. An empty JSON object.

B. A default stock image URL.

C. `None`.

D. A local file path.

Your answer: c


2. Why does the function build `seed_source = f"{barcode or ''}:{name}"`?

A. To randomize every request completely.

B. To create a stable seed source tied to product identity.

C. To encrypt API credentials.

D. To avoid URL encoding.

Your answer:b


3. How is the final numeric `seed` generated?

A. From current timestamp only.

B. From the first 8 hex chars of SHA-256 digest converted to int.

C. By counting prompt words.

D. By summing ASCII codes of model name.

Your answer:b


4. What is the intent of the long prompt text?

A. Request a grocery-style clean packshot with minimal background clutter.

B. Ask for abstract artwork.

C. Force low-resolution thumbnail output.

D. Describe nutrition labels for OCR.

Your answer:a


5. Why use `urllib.parse.quote(prompt, safe="")`?

A. To decode response bytes.

B. To safely URL-encode prompt text for path usage.

C. To remove punctuation permanently from prompt meaning.

D. To choose fallback model automatically.

Your answer:b


6. Which query parameters are included in the generated URL?

A. `model=flux`, `width=1024`, `height=1024`, `seed`, `nologo=true`.

B. `quality=low`, `fps=30`.

C. `camera=rear`, `flash=off`.

D. `risk=high`, `shelf_life=7days`.

Your answer:a


7. What is the returned value type on success?

A. `dict`

B. `bytes`

C. `str` URL

D. `list[str]`

Your answer:c
