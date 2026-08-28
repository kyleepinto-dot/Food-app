# open_food_facts.py Quiz

Use [open_food_facts.py](open_food_facts.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. What does `_looks_like_food(product)` primarily guard against?

A. Network timeouts.

B. Returning non-food or empty records as valid products.

C. Invalid JSON syntax.

D. Duplicate barcodes in memory.

Your answer: b


2. What is the purpose of `_normalize_text(value)`?

A. Keep only alphanumeric/space characters in lowercase and collapse whitespace.

B. Translate text into multiple languages.

C. Encode image URLs.

D. Convert JSON to bytes.

Your answer:a


3. In `_search_food_candidate_score()`, what strongly boosts ranking?

A. Exact normalized match with `product_name` or `generic_name`.

B. Having more than one image only.

C. Product code length over 12.

D. Presence of emojis in categories.

Your answer:a


4. Why does `_build_query_variants()` generate alternatives like reversed tokens and yogurt/yoghurt spellings?

A. To reduce memory usage.

B. To improve manual name search recall when indexing/spelling differs.

C. To prevent HTTP requests.

D. To force barcode-only matching.

Your answer:b


5. What does `_pick_best_image_url(product)` try to do?

A. Remove all images from payload.

B. Prefer high-quality front images and return the first valid HTTP(S) URL.

C. Always return a local file path.

D. Download image bytes directly.

Your answer:b


6. In `fetch_food_product(barcode)`, what causes an early `None` return?

A. API payload status is not `1`.

B. Product has categories.

C. Product has an image.

D. Barcode is numeric.

Your answer:a


7. Why is `_is_acceptable_name_search_result()` more permissive than barcode lookup?

A. Name search can be sparse, so it allows identifiable food-like records with partial metadata.

B. It is only used in debug mode.

C. It disables food checks entirely.

D. It only accepts products with nutriments.

Your answer:a


8. In `fetch_food_product_by_name()`, why are candidates sorted by score descending?

A. To prefer newest API responses.

B. To choose the strongest semantic match rather than first result order.

C. To reduce URL encoding time.

D. To bypass JSON parsing.

Your answer:b


9. What does this line help preserve for search intent?

`score += max(0, 10 - (variant_index * 2))`

A. Earlier query variants get a small confidence bonus.

B. All variants get the same score.

C. Later variants are always preferred.

D. Image-rich products are excluded.

Your answer:a


10. When an image URL is found, what extra field is set on product results?

A. `thumbnail_base64`

B. `best_image_url`

C. `default_icon`

D. `profile_picture`

Your answer:b
