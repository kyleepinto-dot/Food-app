import re

import cv2
import numpy as np

import db
from pages.ai_food_profile_service import get_ai_food_profile_service_signature


PRODUCT_IMAGE_MAX_DIMENSION = 1024
PRODUCT_IMAGE_JPEG_QUALITIES = (82, 74, 66, 58)
AI_PROFILE_GUIDANCE_VERSION = 2


def normalize_barcode(barcode: str) -> str:
    """Normalize UPC-A to its equivalent EAN-13 cache identity."""

    text = str(barcode or "").strip()
    digits = re.sub(r"\D", "", text)
    if digits and len(digits) == 12:
        return f"0{digits}"
    return digits or text.casefold()


def product_cache_key(product: dict | None = None, barcode_hint: str = "") -> str:
    product_data = product if isinstance(product, dict) else {}
    barcode = normalize_barcode(barcode_hint or str(product_data.get("code") or ""))
    if barcode:
        return f"barcode:{barcode}"

    name = str(product_data.get("product_name") or product_data.get("generic_name") or "").strip()
    categories = str(product_data.get("categories") or "").strip()
    normalized_name = " ".join(name.casefold().split())
    normalized_categories = " ".join(categories.casefold().split())
    if not normalized_name:
        raise ValueError("A product cache key requires a barcode or product name")
    return f"name:{normalized_name}|{normalized_categories}"


def store_product(product: dict, barcode_hint: str = "") -> str:
    cache_key = product_cache_key(product, barcode_hint)
    barcode = normalize_barcode(barcode_hint or str(product.get("code") or "")) or None
    db.save_product_scan_cache(cache_key, barcode, product)
    product["_product_cache_key"] = cache_key
    return cache_key


def load_product(barcode: str) -> dict | None:
    cache_key = product_cache_key(barcode_hint=barcode)
    cached = db.load_product_scan_cache(cache_key)
    if cached is None:
        return None

    product = dict(cached["product"])
    product["_product_cache_key"] = cache_key
    profile = cached.get("ai_profile")
    if (
        isinstance(profile, dict)
        and profile.get("_guidance_version") == AI_PROFILE_GUIDANCE_VERSION
        and profile.get("_service_input_signature")
        == get_ai_food_profile_service_signature()
    ):
        product["ai_food_profile"] = dict(profile)
        product["ai_food_profile_cached"] = True
        provider_mode = str(profile.get("_provider") or "remote").lower()
        product["ai_food_profile_status"] = "ready_local" if provider_mode == "local" else "ready"
    cached_images = db.load_product_image_cache(cache_key)
    off_image = cached_images.get("open_food_facts")
    if isinstance(off_image, bytes):
        product["_cached_off_image_data"] = off_image
    ai_image = cached_images.get("ai")
    if isinstance(ai_image, bytes):
        product["_cached_ai_image_data"] = ai_image
    return product


def load_ai_profile(product: dict) -> dict | None:
    cache_key = str(product.get("_product_cache_key") or product_cache_key(product))
    cached = db.load_product_scan_cache(cache_key)
    if cached is None:
        return None
    profile = cached.get("ai_profile")
    if (
        not isinstance(profile, dict)
        or profile.get("_guidance_version") != AI_PROFILE_GUIDANCE_VERSION
        or profile.get("_service_input_signature")
        != get_ai_food_profile_service_signature()
    ):
        return None
    return dict(profile)


def store_ai_profile(product: dict, profile: dict) -> None:
    cache_key = str(product.get("_product_cache_key") or product_cache_key(product))
    cached_profile = dict(profile)
    cached_profile["_guidance_version"] = AI_PROFILE_GUIDANCE_VERSION
    cached_profile["_service_input_signature"] = get_ai_food_profile_service_signature()
    db.save_product_ai_profile(cache_key, cached_profile)
    product["_product_cache_key"] = cache_key


def prepare_image_for_cache(image_data: bytes) -> bytes | None:
    """Resize and JPEG-compress an image to the product cache limits."""

    encoded = np.frombuffer(image_data, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        return None

    height, width = image.shape[:2]
    largest_dimension = max(height, width)
    if largest_dimension > PRODUCT_IMAGE_MAX_DIMENSION:
        scale = PRODUCT_IMAGE_MAX_DIMENSION / largest_dimension
        image = cv2.resize(
            image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    for quality in PRODUCT_IMAGE_JPEG_QUALITIES:
        saved, compressed = cv2.imencode(
            ".jpg",
            image,
            [cv2.IMWRITE_JPEG_QUALITY, quality],
        )
        if saved:
            compressed_bytes = compressed.tobytes()
            if len(compressed_bytes) <= db.PRODUCT_IMAGE_CACHE_MAX_ITEM_BYTES:
                return compressed_bytes
    return None


def store_product_image(product: dict, image_source: str, image_data: bytes) -> bytes:
    cache_key = str(product.get("_product_cache_key") or product_cache_key(product))
    compressed = prepare_image_for_cache(image_data)
    if compressed is None:
        raise ValueError("Product image could not be compressed within cache limits")
    db.save_product_image_cache(cache_key, image_source, compressed, "image/jpeg")
    product["_product_cache_key"] = cache_key
    product[
        "_cached_off_image_data" if image_source == "open_food_facts" else "_cached_ai_image_data"
    ] = compressed
    return compressed
