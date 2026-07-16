import json
import urllib.error
import urllib.parse
import urllib.request


def _looks_like_food(product: dict) -> bool:
    # Open Food Facts is food-focused, but this guard avoids false positives
    # when records are empty or missing core food-related fields.
    if not product.get("product_name"):
        return False

    return bool(
        product.get("categories")
        or product.get("categories_tags")
        or product.get("food_groups_tags")
        or product.get("ingredients_text")
        or product.get("nutriments")
    )


def _normalize_text(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in (value or ""))
    return " ".join(cleaned.split())


def _search_food_candidate_score(product: dict, query: str) -> int:
    """Return a ranking score for manual name-search candidates."""

    q = _normalize_text(query)
    if not q:
        return 0

    q_tokens = [token for token in q.split() if token]
    if not q_tokens:
        return 0

    name = str(product.get("product_name") or "")
    generic = str(product.get("generic_name") or "")
    brands = str(product.get("brands") or "")
    categories = str(product.get("categories") or "")
    ingredients = str(product.get("ingredients_text") or "")

    haystack = _normalize_text(" ".join([name, generic, brands, categories, ingredients]))
    if not haystack:
        return 0

    score = 0
    if q == _normalize_text(name) or q == _normalize_text(generic):
        score += 80
    if q in haystack:
        score += 35

    matched_tokens = sum(1 for token in q_tokens if token in haystack)
    score += matched_tokens * 10

    if product.get("code"):
        score += 3
    if product.get("image_url") or product.get("image_front_url"):
        score += 2

    return score


def _is_acceptable_name_search_result(product: dict) -> bool:
    """Manual search is more permissive than barcode lookup.

    Search hits can be sparse, so accept items that still look like identifiable
    food products even if some metadata fields are missing.
    """

    if _looks_like_food(product):
        return True

    if product.get("product_name") and (
        product.get("categories")
        or product.get("categories_tags")
        or product.get("food_groups_tags")
        or product.get("image_url")
        or product.get("image_front_url")
    ):
        return True

    return False


def _build_query_variants(query: str) -> list[str]:
    """Create fallback variants for manual product name lookup."""

    normalized = _normalize_text(query)
    tokens = [token for token in normalized.split() if token]
    variants: list[str] = []

    def add(value: str) -> None:
        v = _normalize_text(value)
        if len(v) < 2:
            return
        if v not in variants:
            variants.append(v)

    # Original query first (highest intent).
    add(query)
    add(normalized)

    if len(tokens) >= 2:
        # Reordered tokens can recover results where OFF indexing order differs.
        add(" ".join(reversed(tokens)))

    if len(tokens) >= 3:
        # Try compact two-token windows when full phrase is too specific.
        add(" ".join(tokens[:2]))
        add(" ".join(tokens[-2:]))

    # Common regional spelling fallback.
    if "yogurt" in normalized:
        add(normalized.replace("yogurt", "yoghurt"))
    if "yoghurt" in normalized:
        add(normalized.replace("yoghurt", "yogurt"))

    return variants


def _looks_like_named_food_product(product: dict) -> bool:
    """Very loose fallback gate for sparse search records."""

    if not product.get("product_name"):
        return False

    text = _normalize_text(
        " ".join(
            [
                str(product.get("product_name") or ""),
                str(product.get("generic_name") or ""),
                str(product.get("categories") or ""),
            ]
        )
    )
    if not text:
        return False

    obvious_non_food = ["shampoo", "soap", "detergent", "cleaner", "toothpaste", "deodorant"]
    return not any(token in text for token in obvious_non_food)


def _pick_best_image_url(product: dict) -> str | None:
    # Prefer high-resolution front image fields when available.
    candidates = [
        product.get("image_front_url"),
        product.get("image_url"),
        product.get("image_front_small_url"),
    ]

    selected_images = product.get("selected_images")
    if isinstance(selected_images, dict):
        front = selected_images.get("front")
        if isinstance(front, dict):
            display = front.get("display")
            if isinstance(display, dict):
                # English first, then any available display entry.
                candidates.insert(0, display.get("en"))
                for value in display.values():
                    candidates.append(value)

    for url in candidates:
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
    return None


def fetch_food_product(barcode: str) -> dict | None:
    """Fetch one barcode from Open Food Facts and return product data if food.

    Returns None when barcode is not found, not a food item, or request fails.
    """

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PantryIQ-Connect/1.0 (github.com/kyleepinto-dot/Food-app)",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None

    if payload.get("status") != 1:
        return None

    product = payload.get("product")
    if not isinstance(product, dict):
        return None

    if not _looks_like_food(product):
        return None

    image_url = _pick_best_image_url(product)
    if image_url:
        product["best_image_url"] = image_url

    return product


def fetch_food_product_by_name(query: str) -> dict | None:
    """Search Open Food Facts by product name and return first food match."""

    text = (query or "").strip()
    if len(text) < 2:
        return None

    query_variants = _build_query_variants(text)
    candidates: list[tuple[int, dict]] = []

    for variant_index, variant in enumerate(query_variants):
        encoded = urllib.parse.quote(variant)
        url = (
            "https://world.openfoodfacts.org/cgi/search.pl"
            f"?search_terms={encoded}&search_simple=1&action=process&json=1&page_size=24"
        )
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "PantryIQ-Connect/1.0 (github.com/kyleepinto-dot/Food-app)",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            continue

        products = payload.get("products")
        if not isinstance(products, list):
            continue

        for item in products:
            if not isinstance(item, dict):
                continue

            if not _is_acceptable_name_search_result(item) and not _looks_like_named_food_product(item):
                continue

            score = _search_food_candidate_score(item, text)
            if score <= 0:
                continue

            # Earlier variants represent higher-confidence user intent.
            score += max(0, 10 - (variant_index * 2))
            candidates.append((score, item))

    if not candidates:
        return None

    # Prefer the strongest semantic match instead of first API result.
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    item = candidates[0][1]

    image_url = _pick_best_image_url(item)
    if image_url:
        item["best_image_url"] = image_url
    return item
