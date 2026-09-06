import hashlib
import urllib.parse


def build_ai_food_image_url(food_name: str, barcode: str | None = None) -> str | None:
    """Return an AI-generated image URL for a food item name.

    The URL uses a hosted image generation endpoint and includes a stable seed
    so the same barcode tends to return a consistent result.
    """

    name = (food_name or "").strip()
    if not name:
        return None

    seed_source = f"{barcode or ''}:{name}".encode("utf-8")
    seed = int(hashlib.sha256(seed_source).hexdigest()[:8], 16)

    prompt = (
        f"E-commerce retail packshot of {name}, front-facing product as sold in grocery stores, "
        "centered composition, isolated subject, plain white or transparent background style, "
        "photorealistic, sharp edges, no props, no table, no kitchen scene, no hands, no shadow clutter, "
        "no extra objects, no watermark"
    )

    encoded_prompt = urllib.parse.quote(prompt, safe="")
    params = urllib.parse.urlencode(
        {
            "model": "flux",
            "width": 1024,
            "height": 1024,
            "seed": seed,
            "nologo": "true",
        }
    )
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?{params}"


def build_ai_meal_image_url(meal_name: str, ingredients: list[str]) -> str | None:
    """Return a stable AI-generated photo URL for a suggested meal."""

    name = (meal_name or "").strip()
    if not name:
        return None

    ingredient_text = ", ".join(str(item).strip() for item in ingredients[:6] if str(item).strip())
    seed_source = f"meal:{name}:{ingredient_text}".encode("utf-8")
    seed = int(hashlib.sha256(seed_source).hexdigest()[:8], 16)
    prompt = (
        f"Appetizing photorealistic food photography of {name}, made with {ingredient_text or 'healthy pantry ingredients'}, "
        "nutritionally balanced meal, colorful vegetables, natural presentation, single plated serving, "
        "soft daylight, clean neutral background, realistic portions, no people, no text, no watermark"
    )
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    params = urllib.parse.urlencode(
        {
            "model": "flux",
            # The planner displays small thumbnails and a short detail banner;
            # a smaller source image generates and transfers much faster.
            "width": 640,
            "height": 480,
            "seed": seed,
            "nologo": "true",
        }
    )
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?{params}"
