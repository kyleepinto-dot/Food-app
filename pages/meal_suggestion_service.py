"""AI-backed meal planning helpers for pantry inventory."""

from datetime import datetime, timezone
import json
import re
import urllib.error
import urllib.parse
import urllib.request


_DEFAULT_SHELF_LIFE_DAYS = 7


def _shelf_life_days(value: str) -> int:
    """Return the conservative (earliest) duration represented by shelf-life text."""

    text = str(value or "").strip().lower()
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match is None:
        return _DEFAULT_SHELF_LIFE_DAYS

    amount = float(match.group(1))
    if "month" in text:
        amount *= 30
    elif "week" in text:
        amount *= 7
    elif "hour" in text:
        amount /= 24
    return max(1, round(amount))


def _age_days(value: str) -> int:
    try:
        added_at = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if added_at.tzinfo is None:
            added_at = added_at.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - added_at.astimezone(timezone.utc)).days)
    except (TypeError, ValueError):
        return 0


def rank_pantry_items(pantry_items: list[dict]) -> list[dict]:
    """Copy and rank pantry items by their estimated earliest expiration."""

    ranked: list[dict] = []
    risk_priority = {"High Risk": 0, "Medium Risk": 1, "Low Risk": 2}
    for item in pantry_items:
        if not isinstance(item, dict):
            continue
        shelf_life = str(item.get("shelf_life") or "5-10 days")
        days_remaining = max(0, _shelf_life_days(shelf_life) - _age_days(str(item.get("added_at") or "")))
        ranked_item = dict(item)
        ranked_item["shelf_life"] = shelf_life
        ranked_item["days_remaining"] = days_remaining
        ranked_item["expiry_label"] = "Use today" if days_remaining == 0 else f"Use in about {days_remaining} day{'s' if days_remaining != 1 else ''}"
        ranked.append(ranked_item)

    return sorted(
        ranked,
        key=lambda item: (
            int(item.get("days_remaining") or 0),
            risk_priority.get(str(item.get("risk") or "Medium Risk"), 1),
            str(item.get("name") or ""),
        ),
    )


def _extract_json_object(raw_text: str) -> dict | None:
    try:
        payload = json.loads(raw_text)
        if isinstance(payload, dict):
            return payload
    except (TypeError, ValueError):
        pass

    match = re.search(r"\{[\s\S]*\}", str(raw_text or ""))
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _text(value, default: str) -> str:
    result = str(value or "").strip()
    return result if result else default


def _normalize_suggestion(payload: dict, ranked_items: list[dict]) -> dict:
    available_names = [str(item.get("name") or "Food item") for item in ranked_items]
    raw_pantry_items = payload.get("pantry_items_used")
    pantry_items_used = (
        [str(value).strip() for value in raw_pantry_items if str(value).strip()]
        if isinstance(raw_pantry_items, list)
        else []
    )
    if not pantry_items_used:
        pantry_items_used = available_names[:4]

    raw_ingredients = payload.get("ingredients")
    ingredients: list[dict] = []
    if isinstance(raw_ingredients, list):
        for value in raw_ingredients:
            if isinstance(value, dict):
                name = _text(value.get("name"), "Ingredient")
                amount = _text(value.get("amount"), "As needed")
            else:
                name = _text(value, "Ingredient")
                amount = "As needed"
            ingredients.append({"name": name, "amount": amount})
    if not ingredients:
        ingredients = [{"name": name, "amount": "1 serving portion"} for name in pantry_items_used]

    raw_directions = payload.get("directions") or payload.get("instructions")
    directions = [str(value).strip() for value in raw_directions if str(value).strip()] if isinstance(raw_directions, list) else []
    if not directions:
        directions = ["Prepare and measure every ingredient.", "Cook until safely done and serve promptly."]

    return {
        "title": _text(payload.get("title"), "Healthy Pantry Meal"),
        "description": _text(payload.get("description"), "A balanced meal that prioritizes the pantry items expiring first."),
        "pantry_items_used": pantry_items_used[:8],
        "ingredients": ingredients[:16],
        "directions": directions[:12],
        "prep_time": _text(payload.get("prep_time"), "About 30 minutes"),
        "nutrition_notes": _text(
            payload.get("nutrition_notes"),
            "Pair protein, fiber-rich carbohydrates, and vegetables for a balanced plate.",
        ),
        "food_safety_note": _text(
            payload.get("food_safety_note"),
            "Check every ingredient for spoilage and cook per package food-safety guidance.",
        ),
        "priority_items": available_names[:3],
        "provider": "remote",
    }


def _fallback_suggestions(ranked_items: list[dict]) -> list[dict]:
    names = [str(item.get("name") or "Food item") for item in ranked_items[:4]]
    featured = ", ".join(names) if names else "your pantry items"
    meal_templates = [
        ("Healthy Use-It-First Pantry Bowl", "Cooked brown rice", "1 cup"),
        ("Quick Pantry Stir-Fry", "Low-sodium soy sauce", "1 tablespoon"),
        ("Fresh Pantry Wraps", "Whole-grain tortillas", "4 small"),
        ("Colorful Pantry Salad", "Mixed leafy greens", "4 cups"),
        ("Hearty Pantry Soup", "Low-sodium vegetable broth", "4 cups"),
        ("Baked Pantry Skillet", "Extra-virgin olive oil", "1 tablespoon"),
    ]
    return [
        {
            "title": title,
            "description": f"A flexible, balanced meal designed to use {featured} before fresher pantry items.",
            "pantry_items_used": names,
            "ingredients": [
                *[{"name": name, "amount": "1 cup prepared"} for name in names],
                {"name": extra_name, "amount": extra_amount},
                {"name": "Black pepper", "amount": "1/4 teaspoon"},
            ],
            "directions": [
                "Inspect every ingredient and discard anything with signs of spoilage.",
                "Wash produce under cool running water, then measure and prepare all ingredients as listed.",
                "Heat a large pan over medium heat for 2 minutes and add the prepared ingredients.",
                "Cook for 8 to 12 minutes, stirring every 2 minutes, until vegetables are tender and proteins reach a safe temperature.",
                "Remove from heat, season with black pepper, divide into four portions, and serve immediately.",
            ],
            "prep_time": "About 25 minutes",
            "nutrition_notes": "Include vegetables, protein, and fiber-rich carbohydrates while limiting added salt and sugar.",
            "food_safety_note": "An expiry estimate is not a safety guarantee; inspect food and follow package storage and cooking directions.",
            "priority_items": names[:3],
            "provider": "local",
        }
        for title, extra_name, extra_amount in meal_templates
    ]


def fetch_ai_meal_suggestions(pantry_items: list[dict]) -> list[dict]:
    """Suggest six nutritious meals that prioritize earliest-expiring items."""

    ranked_items = rank_pantry_items(pantry_items)
    if not ranked_items:
        return []

    inventory_lines = []
    for item in ranked_items[:12]:
        inventory_lines.append(
            f"- {item.get('name', 'Food item')} (quantity {item.get('quantity', 1)}, "
            f"category {item.get('category', 'Food item')}, risk {item.get('risk', 'Medium Risk')}, "
            f"estimated {item.get('expiry_label', 'use soon')})"
        )

    prompt = (
        "You are a careful meal-planning and nutrition assistant. Suggest SIX distinct, practical, healthy, "
        "nutritionally balanced meals using only sensible combinations from this pantry. Prioritize the "
        "items listed first because they are estimated to expire first. Favor vegetables, fiber, and lean "
        "or plant protein; limit added sugar, saturated fat, and sodium. Never claim food is safe based only "
        "on an estimated date, and include inspection and safe-cooking guidance. Return ONLY minified JSON as "
        "an object with one key named meals. meals must contain exactly six objects, each with keys "
        "title,description,pantry_items_used,ingredients,directions,prep_time,nutrition_notes,food_safety_note. "
        "pantry_items_used must only name items from the supplied pantry. ingredients must list ALL pantry and "
        "non-pantry ingredients as objects with name and precise amount keys for four servings. directions must "
        "be an array of detailed numbered-order steps with times, temperatures, and doneness cues where relevant. "
        "Common non-pantry ingredients may be added when needed. Pantry inventory:\n"
        + "\n".join(inventory_lines)
    )
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    request = urllib.request.Request(
        f"https://text.pollinations.ai/{encoded_prompt}",
        headers={"User-Agent": "PantryIQ-Connect/1.0 (github.com/kyleepinto-dot/Food-app)"},
    )

    for timeout_seconds in (8, 12):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = _extract_json_object(response.read().decode("utf-8", errors="ignore"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("meals"), list):
            suggestions = [
                _normalize_suggestion(meal, ranked_items)
                for meal in payload["meals"][:8]
                if isinstance(meal, dict)
            ]
            if 3 <= len(suggestions) <= 8:
                return suggestions

    return _fallback_suggestions(ranked_items)
