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


def _food_role(name: str) -> str:
    text = name.lower()
    role_keywords = {
        "protein": ("chicken", "beef", "pork", "turkey", "fish", "salmon", "tuna", "tofu", "bean", "lentil", "chickpea", "egg"),
        "starch": ("rice", "pasta", "noodle", "potato", "tortilla", "bread", "quinoa", "couscous", "oat"),
        "vegetable": ("spinach", "tomato", "broccoli", "mushroom", "pepper", "onion", "carrot", "corn", "kale", "lettuce", "cabbage", "zucchini", "pea", "cucumber", "cauliflower", "celery", "asparagus", "squash"),
        "fruit": ("apple", "banana", "orange", "berry", "berries", "mango", "pear", "peach", "melon"),
        "dairy": ("milk", "cheese", "yogurt", "cream"),
    }
    for role, keywords in role_keywords.items():
        if any(keyword in text for keyword in keywords):
            return role
    return "other"


def _meal_type(payload: dict) -> str:
    """Classify a suggestion so balance requirements apply only to main dishes."""

    declared = str(payload.get("meal_type") or payload.get("course") or "").strip().casefold()
    if declared in {"dessert", "desserts", "sweet"}:
        return "dessert"
    if declared in {"appetizer", "appetizers", "starter", "snack"}:
        return "appetizer"

    meal_text = f"{payload.get('title', '')} {payload.get('description', '')}".casefold()
    dessert_words = ("dessert", "cake", "cookie", "brownie", "crisp", "cobbler", "pudding", "sorbet", "ice cream")
    appetizer_words = ("appetizer", "starter", "bite", "dip", "bruschetta", "crostini", "canape")
    if any(word in meal_text for word in dessert_words):
        return "dessert"
    if any(word in meal_text for word in appetizer_words):
        return "appetizer"
    return "main"


def _is_seasoning(name: str) -> bool:
    text = name.casefold()
    seasoning_words = (
        "paprika", "cumin", "thyme", "rosemary", "oregano", "basil", "coriander",
        "turmeric", "cinnamon", "ginger", "garlic", "chili", "seasoning", "herb", "spice",
    )
    return any(word in text for word in seasoning_words)


def _balance_main_ingredients(title: str, ingredients: list[dict]) -> tuple[list[dict], list[str]]:
    """Suggest missing protein, vegetables, and seasoning for a complete main dish."""

    ingredient_names = [str(ingredient.get("name") or "") for ingredient in ingredients]
    roles = {_food_role(name) for name in ingredient_names}
    title_text = title.casefold()
    if "taco" in title_text:
        defaults = (("Black beans", "1 can, drained"), ("Bell peppers", "2, sliced"), ("Ground cumin", "1 teaspoon"))
    elif "pasta" in title_text or "noodle" in title_text:
        defaults = (("Cannellini beans", "1 can, drained"), ("Baby spinach", "4 cups"), ("Italian seasoning", "1 teaspoon"))
    elif "soup" in title_text or "stew" in title_text:
        defaults = (("Lentils", "1 cup, rinsed"), ("Carrots", "2, diced"), ("Dried thyme", "1 teaspoon"))
    elif "salad" in title_text:
        defaults = (("Chickpeas", "1 can, drained"), ("Cucumber", "1, chopped"), ("Dried oregano", "1 teaspoon"))
    else:
        defaults = (("Chickpeas", "1 can, drained"), ("Broccoli florets", "3 cups"), ("Smoked paprika", "1 teaspoon"))

    additions: list[dict] = []
    if "protein" not in roles:
        additions.append({"name": defaults[0][0], "amount": defaults[0][1]})
    if "vegetable" not in roles:
        additions.append({"name": defaults[1][0], "amount": defaults[1][1]})
    if not any(_is_seasoning(name) for name in ingredient_names):
        additions.append({"name": defaults[2][0], "amount": defaults[2][1]})

    available_slots = max(0, 16 - len(additions))
    return ingredients[:available_slots] + additions, [str(item["name"]) for item in additions]


def _estimate_recipe_time(title: str, ingredients: list[dict], directions: list[str]) -> str:
    """Estimate total preparation and cooking time from the actual recipe."""

    direction_text = " ".join(str(step) for step in directions)
    time_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:(?:to|-)\s*(\d+(?:\.\d+)?)\s*)?(seconds?|minutes?|hours?)\b",
        re.IGNORECASE,
    )
    cooking_minimum = 0.0
    cooking_maximum = 0.0
    for match in time_pattern.finditer(direction_text):
        lower = float(match.group(1))
        upper = float(match.group(2) or match.group(1))
        unit = match.group(3).casefold()
        multiplier = 60.0 if unit.startswith("hour") else (1.0 / 60.0 if unit.startswith("second") else 1.0)
        cooking_minimum += lower * multiplier
        cooking_maximum += upper * multiplier

    if cooking_maximum < 6:
        title_text = title.casefold()
        method_ranges = (
            (("roast", "bake", "casserole"), (25, 40)),
            (("soup", "stew", "chili"), (20, 35)),
            (("pasta", "noodle"), (15, 25)),
            (("skillet", "stir-fry", "stir fry"), (12, 20)),
            (("taco", "quesadilla"), (10, 18)),
            (("salad", "sandwich", "wrap"), (0, 5)),
        )
        cooking_minimum, cooking_maximum = next(
            (time_range for keywords, time_range in method_ranges if any(keyword in title_text for keyword in keywords)),
            (15, 25),
        )

    preparation_minutes = 5 + min(10, ((max(1, len(ingredients)) + 2) // 3) * 5)

    def round_up_five(value: float) -> int:
        return max(5, int((value + 4.999) // 5) * 5)

    minimum = round_up_five(preparation_minutes + cooking_minimum)
    maximum = round_up_five(preparation_minutes + cooking_maximum)
    if minimum == maximum:
        return f"Estimated {minimum} minutes"
    return f"Estimated {minimum}-{maximum} minutes"


def _unique_title(title: str, pantry_items_used: list[str], used_titles: set[str]) -> str:
    candidate = title
    suffix = pantry_items_used[0] if pantry_items_used else "Pantry"
    number = 2
    while candidate.casefold() in used_titles:
        candidate = f"{title} with {suffix}" if number == 2 else f"{title} with {suffix} {number}"
        number += 1
    used_titles.add(candidate.casefold())
    return candidate


def _normalize_suggestion(payload: dict, ranked_items: list[dict]) -> dict:
    available_names = [str(item.get("name") or "Food item") for item in ranked_items]
    available_lookup = {name.casefold(): name for name in available_names}
    raw_pantry_items = payload.get("pantry_items_used")
    pantry_items_used = (
        [available_lookup[str(value).strip().casefold()] for value in raw_pantry_items if str(value).strip().casefold() in available_lookup]
        if isinstance(raw_pantry_items, list)
        else []
    )
    if not pantry_items_used:
        pantry_items_used = available_names[:1]
    pantry_items_used = pantry_items_used[:3]
    selected_lookup = {name.casefold() for name in pantry_items_used}

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
            if name.casefold() in available_lookup and name.casefold() not in selected_lookup:
                continue
            ingredients.append({"name": name, "amount": amount})
    ingredient_names = {ingredient["name"].casefold() for ingredient in ingredients}
    pantry_ingredients = [
        {"name": name, "amount": "1 serving portion"}
        for name in pantry_items_used
        if name.casefold() not in ingredient_names
    ]
    ingredients = pantry_ingredients + ingredients
    title = _text(payload.get("title"), "Healthy Pantry Meal")
    meal_type = _meal_type(payload)
    balance_additions: list[str] = []
    if meal_type == "main":
        ingredients, balance_additions = _balance_main_ingredients(title, ingredients)

    raw_directions = payload.get("directions") or payload.get("instructions")
    directions = [str(value).strip() for value in raw_directions if str(value).strip()] if isinstance(raw_directions, list) else []
    if not directions:
        directions = ["Prepare and measure every ingredient.", "Cook until safely done and serve promptly."]
    if balance_additions:
        directions.append(
            f"Add {', '.join(balance_additions)} during cooking so the finished main dish includes its suggested protein, vegetables, and seasoning."
        )
    prep_time = _estimate_recipe_time(title, ingredients, directions)

    return {
        "title": title,
        "meal_type": meal_type,
        "description": _text(payload.get("description"), "A balanced meal that prioritizes the pantry items expiring first."),
        "pantry_items_used": pantry_items_used,
        "ingredients": ingredients,
        "directions": directions[:12],
        "prep_time": prep_time,
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


def _fallback_suggestions(ranked_items: list[dict], variation: int = 0) -> list[dict]:
    names = [str(item.get("name") or "Food item") for item in ranked_items[:12]]
    by_role = {role: [name for name in names if _food_role(name) == role] for role in ("protein", "starch", "vegetable", "fruit", "dairy", "other")}

    def pick(role: str, offset: int = 0) -> str | None:
        choices = by_role[role]
        return choices[(variation + offset) % len(choices)] if choices else None

    def pick_matching(role: str, keywords: tuple[str, ...], offset: int = 0) -> str | None:
        choices = [name for name in by_role[role] if any(keyword in name.lower() for keyword in keywords)]
        return choices[(variation + offset) % len(choices)] if choices else None

    def subset(*values: str | None) -> list[str]:
        selected: list[str] = []
        for value in values:
            if value and value not in selected:
                selected.append(value)
        if not selected and names:
            selected.append(names[variation % len(names)])
        return selected[:3]

    def role_aware_directions(kind: str, pantry_used: list[str]) -> list[str]:
        """Build steps that name only ingredients and food roles present in the recipe."""

        item_names = ", ".join(pantry_used)
        proteins = ", ".join(name for name in pantry_used if _food_role(name) == "protein")
        vegetables = ", ".join(name for name in pantry_used if _food_role(name) == "vegetable")
        starches = ", ".join(name for name in pantry_used if _food_role(name) == "starch")

        if kind == "skillet":
            cook_first = (
                f"Add {proteins} and cook until browned and safely cooked through, then transfer to a clean plate."
                if proteins
                else f"Add {item_names} and saute for 5 to 7 minutes until tender and lightly browned."
            )
            finish = (
                f"Add {vegetables}, garlic, and smoked paprika; saute for 5 to 7 minutes until crisp-tender."
                if vegetables and proteins
                else "Add the garlic and smoked paprika and cook for 1 minute until fragrant."
            )
            return [
                f"Prepare {item_names} in even bite-size pieces.",
                f"Heat olive oil in a large skillet over medium-high heat. {cook_first}",
                finish,
                f"Combine {item_names} in the skillet, toss until hot throughout, and serve.",
            ]
        if kind == "soup":
            return [
                f"Prepare {item_names}; drain canned items and cut fresh items into bite-size pieces.",
                f"Warm olive oil in a soup pot over medium heat and cook {item_names} for 5 minutes.",
                "Add the vegetable broth and thyme, bring to a boil, then reduce to a gentle simmer.",
                f"Simmer for 15 to 25 minutes until {item_names} is tender and safely cooked, then serve hot.",
            ]
        if kind == "tacos":
            return [
                f"Prepare {item_names} as a taco filling and pat away excess moisture.",
                f"Cook {item_names} with cumin in a skillet over medium-high heat until tender and safely done.",
                "Warm the corn tortillas in a dry skillet for about 20 seconds per side.",
                f"Divide {item_names} among the tortillas, finish with lime, and serve immediately.",
            ]
        if kind == "pasta":
            return [
                "Boil the whole-wheat pasta until al dente according to its package; reserve 1/2 cup cooking water.",
                f"Saute {item_names} in a wide pan over medium heat until tender and safely cooked.",
                "Stir in the crushed tomatoes and Italian seasoning and simmer for 8 minutes.",
                f"Toss the pasta and {item_names} with the sauce, loosening with reserved water as needed.",
            ]
        if kind == "roast":
            roast_parts = ", ".join(filter(None, (vegetables, starches, proteins))) or item_names
            return [
                f"Heat the oven to 425 F (220 C) and prepare {roast_parts} in even-size pieces.",
                f"Toss {roast_parts} with olive oil and rosemary and spread everything in a single layer.",
                f"Roast {roast_parts} for 20 to 35 minutes until browned, tender, and safely cooked.",
                f"Rest {roast_parts} for 5 minutes, finish with lemon juice, and serve.",
            ]

        prepare_protein = (
            f"Cook {proteins} separately to a safe internal temperature, rest for 5 minutes, and slice."
            if proteins
            else f"Cut {item_names} into fork-size pieces."
        )
        return [
            f"Wash and thoroughly dry {item_names}, as appropriate.",
            prepare_protein,
            "Whisk olive oil and apple cider vinegar in a large bowl, then toss with the mixed leafy greens.",
            f"Arrange {item_names} over the dressed greens and serve immediately.",
        ]

    plans = [
        {
            "kind": "skillet",
            "items": subset(pick("protein"), pick("vegetable")),
            "extra": [("Olive oil", "1 tablespoon"), ("Smoked paprika", "1 teaspoon"), ("Garlic", "2 cloves, minced")],
        },
        {
            "kind": "soup",
            "items": subset(pick("vegetable", 1), pick("protein", 1), pick("starch")),
            "extra": [("Low-sodium vegetable broth", "6 cups"), ("Dried thyme", "1 teaspoon"), ("Olive oil", "1 tablespoon")],
        },
        {
            "kind": "tacos",
            "items": subset(pick("protein", 2), pick("vegetable", 2), pick("dairy")),
            "extra": [("Corn tortillas", "8 small"), ("Ground cumin", "1 teaspoon"), ("Lime", "1, cut into wedges")],
        },
        {
            "kind": "pasta",
            "items": subset(pick("vegetable", 3), pick("protein", 3)),
            "extra": [("Whole-wheat pasta", "12 ounces"), ("Crushed tomatoes", "2 cups"), ("Italian seasoning", "1 teaspoon")],
        },
        {
            "kind": "roast",
            "items": subset(
                pick_matching("vegetable", ("broccoli", "carrot", "cauliflower", "zucchini", "pepper", "onion", "mushroom", "tomato"), 4),
                pick_matching("starch", ("potato",)),
                pick("protein", 4),
            ),
            "extra": [("Olive oil", "2 tablespoons"), ("Dried rosemary", "1 teaspoon"), ("Lemon", "1")],
        },
        {
            "kind": "salad",
            "items": subset(pick("vegetable", 5), pick("fruit"), pick("protein", 5)),
            "extra": [("Mixed leafy greens", "6 cups"), ("Olive oil", "2 tablespoons"), ("Apple cider vinegar", "1 tablespoon")],
        },
    ]
    adjectives = ("Bright", "Savory", "Garden", "Weeknight", "Zesty", "Homestyle")
    suggestions: list[dict] = []
    for index, plan in enumerate(plans):
        pantry_used = plan["items"]
        lead = pantry_used[0] if pantry_used else "Pantry"
        adjective = adjectives[(variation + index) % len(adjectives)]
        title = f"{adjective} {lead} {str(plan['kind']).title()}"
        directions = role_aware_directions(str(plan["kind"]), pantry_used)
        ingredients = [
            *[{"name": name, "amount": "1 to 2 cups, prepared"} for name in pantry_used],
            *[{"name": name, "amount": amount} for name, amount in plan["extra"]],
        ]
        ingredients, balance_additions = _balance_main_ingredients(title, ingredients)
        if balance_additions:
            directions.append(
                f"Add {', '.join(balance_additions)} during cooking to complete and season the main dish."
            )
        prep_time = _estimate_recipe_time(title, ingredients, directions)
        suggestions.append({
            "title": title,
            "meal_type": "main",
            "description": f"A practical {plan['kind']} using a compatible subset of your pantry rather than forcing every item into one dish.",
            "pantry_items_used": pantry_used,
            "ingredients": ingredients,
            "directions": directions,
            "prep_time": prep_time,
            "nutrition_notes": "Build a balanced serving with vegetables, protein, and a moderate portion of whole-grain carbohydrate when included.",
            "food_safety_note": "Inspect pantry foods before use, prevent raw-protein cross-contamination, and cook proteins to a safe internal temperature.",
            "priority_items": names[:3],
            "provider": "local",
        })
    return suggestions


def fetch_ai_meal_suggestions(pantry_items: list[dict], variation: int = 0) -> list[dict]:
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
        "You are a careful meal-planning and nutrition assistant. Suggest SIX distinct, practical dishes "
        "using only sensible combinations from this pantry. Main dishes should be nutritionally balanced. Prioritize the "
        "items listed first because they are estimated to expire first. Use only ONE TO THREE compatible pantry "
        "items per meal; spread the inventory across the six meals and never combine foods that do not make culinary "
        "sense together. Every title must be unique and specific to its dish, and should differ from prior requests. "
        f"This request's variation number is {variation}. Favor vegetables, fiber, and lean "
        "or plant protein; limit added sugar, saturated fat, and sodium. For each main dish, suggest a compatible "
        "protein, one or more vegetables, and spices or herbs that balance and enhance it, adding them as non-pantry "
        "ingredients when the pantry does not supply them. Desserts and appetizers do not need to be nutritionally "
        "balanced and must not receive forced protein or vegetable additions. Never claim food is safe based only "
        "on an estimated date, and include inspection and safe-cooking guidance. Return ONLY minified JSON as "
        "an object with one key named meals. meals must contain exactly six objects, each with keys "
        "title,meal_type,description,pantry_items_used,ingredients,directions,nutrition_notes,food_safety_note. "
        "meal_type must be exactly main, dessert, or appetizer. "
        "pantry_items_used must only name items from the supplied pantry. ingredients must list ALL pantry and "
        "non-pantry ingredients as objects with name and precise amount keys for four servings. Every item in "
        "pantry_items_used must appear by the exact same name in ingredients. Directions may mention protein, "
        "vegetables, starch, fruit, or dairy only when that role is represented by an ingredient in that meal. directions must "
        "be an array of detailed numbered-order steps with times, temperatures, and doneness cues where relevant. "
        "Directions must be a real recipe tailored to that meal, not generic preparation advice. Vary seasonings and "
        "starches across meals; do not repeatedly default to black pepper or cooked brown rice. Common non-pantry "
        "ingredients may be added when needed. Pantry inventory:\n"
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
            used_titles: set[str] = set()
            for suggestion in suggestions:
                suggestion["title"] = _unique_title(
                    str(suggestion.get("title") or "Pantry Meal"),
                    [str(value) for value in suggestion.get("pantry_items_used") or []],
                    used_titles,
                )
            if 3 <= len(suggestions) <= 8:
                return suggestions

    return _fallback_suggestions(ranked_items, variation)
