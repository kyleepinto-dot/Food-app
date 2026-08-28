# ai_food_profile_service.py Quiz

Use [ai_food_profile_service.py](ai_food_profile_service.py) and answer each question with the correct multiple-choice letter.

After each question there is a blank space for your response.

## Multiple Choice Questions

1. What is `_LAST_PROFILE_ERROR` used for?

A. Storing the last AI profile failure reason for diagnostics.

B. Caching all profile JSON responses.

C. Holding the current barcode value.

D. Tracking UI theme state.

Your answer:a


2. What does `_extract_json_object(text)` support beyond direct JSON parsing?

A. Parsing XML tags.

B. Pulling a JSON object embedded inside explanatory text.

C. Decrypting remote responses.

D. Converting markdown into dicts.

Your answer:b


3. In `_extract_labeled_profile(text)`, when does it return `None`?

A. If required labeled fields like risk/confidence/shelf_life/storage are missing.

B. If warnings are present.

C. If the product name is short.

D. If confidence is medium.

Your answer:a


4. What does `_normalize_risk(value)` output when text contains "high"?

A. `Critical`

B. `High Risk`

C. `High Confidence`

D. `Unsafe`

Your answer:b


5. In `_parse_profile_response(raw_text)`, what happens if no valid JSON/labeled structure is found?

A. The function raises RuntimeError.

B. The function returns `None`.

C. The function returns empty strings.

D. The function retries network calls itself.

Your answer:b


6. Why does `_default_fattom_by_risk(risk)` exist?

A. To derive fallback FATTOM levels from normalized risk category.

B. To compute image dimensions.

C. To sort API results alphabetically.

D. To generate navigation labels.

Your answer:a


7. What does `_build_local_profile(product_name, categories)` provide?

A. A remote API request object.

B. A product-specific local fallback profile when remote AI is unavailable.

C. A barcode scanning pipeline.

D. A cache eviction strategy.

Your answer:b


8. In `fetch_ai_food_profile(...)`, why are two timeout values used `(6, 10)`?

A. To try a faster attempt first, then a slightly longer retry budget.

B. To switch between two AI models.

C. To test two barcode formats.

D. To avoid any network call.

Your answer:a


9. What is returned when remote AI calls fail or parse fails repeatedly?

A. `None`

B. The raw AI text.

C. A local smart profile from `_build_local_profile(...)`.

D. A list of retry URLs.

Your answer:c


10. Which key marks whether parsed profile came from remote or local logic?

A. `_provider`

B. `_status_code`

C. `source_api`

D. `_fallback_only`

Your answer:a
