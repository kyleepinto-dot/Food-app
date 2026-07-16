import json
import urllib.error
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
