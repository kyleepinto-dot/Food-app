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
