import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path


_LAST_PROFILE_ERROR = ""


@lru_cache(maxsize=1)
def get_ai_food_profile_service_signature() -> str:
    """Fingerprint service code so cached outputs expire after behavior changes."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _normalize_factor_level(value: str, default: str = "Medium") -> str:
    text = (value or "").strip().lower()
    if "high" in text:
        return "High"
    if "low" in text:
        return "Low"
    if "medium" in text:
        return "Medium"
    return default


def _default_fattom_by_risk(risk: str) -> dict:
    normalized_risk = _normalize_risk(risk)
    if normalized_risk == "High Risk":
        return {
            "food": "High",
            "acidity": "Medium",
            "time": "High",
            "temperature": "High",
            "oxygen": "Medium",
            "moisture": "High",
        }
    if normalized_risk == "Low Risk":
        return {
            "food": "Low",
            "acidity": "Medium",
            "time": "Low",
            "temperature": "Medium",
            "oxygen": "Low",
            "moisture": "Low",
        }
    return {
        "food": "Medium",
        "acidity": "Medium",
        "time": "Medium",
        "temperature": "Medium",
        "oxygen": "Low",
        "moisture": "Medium",
    }


def _clean_text(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text if text else default


def _normalize_shelf_life_days(value: object) -> dict[str, int | None]:
    payload = value if isinstance(value, dict) else {}
    normalized: dict[str, int | None] = {}
    for state in ("fresh", "unopened", "opened"):
        raw_value = payload.get(state)
        if isinstance(raw_value, bool):
            normalized[state] = None
            continue
        if not isinstance(raw_value, (int, float, str)):
            normalized[state] = None
            continue
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            normalized[state] = None
            continue
        normalized[state] = round(numeric_value) if numeric_value >= 1 else None
    return normalized


def _set_last_error(message: str) -> None:
    global _LAST_PROFILE_ERROR
    _LAST_PROFILE_ERROR = message


def get_last_ai_food_profile_error() -> str:
    return _LAST_PROFILE_ERROR


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None

    # Accept direct JSON or JSON wrapped in explanation text.
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except ValueError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match is None:
        return None

    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_labeled_profile(text: str) -> dict | None:
    """Parse profile from non-JSON AI responses.

    Supported forms:
    - risk: High Risk
    - confidence: Medium Confidence
    - shelf_life: Unopened: follow package date. After opening: 3-7 days.
    - storage: Before opening: refrigerate. After opening: refrigerate and reseal.
    """

    if not text:
        return None

    lowered = text.lower()
    patterns = {
        "risk": r"risk\s*[:=]\s*([^\n\r]+)",
        "confidence": r"confidence\s*[:=]\s*([^\n\r]+)",
        "shelf_life": r"(shelf[_\s-]*life)\s*[:=]\s*([^\n\r]+)",
        "storage": r"storage\s*[:=]\s*([^\n\r]+)",
        "immediate_actions": r"(immediate[_\s-]*actions?)\s*[:=]\s*([^\n\r]+)",
        "warnings": r"warnings?\s*[:=]\s*([^\n\r]+)",
        "fattom_food": r"fattom[_\s-]*food\s*[:=]\s*([^\n\r]+)",
        "fattom_acidity": r"fattom[_\s-]*acidity\s*[:=]\s*([^\n\r]+)",
        "fattom_time": r"fattom[_\s-]*time\s*[:=]\s*([^\n\r]+)",
        "fattom_temperature": r"fattom[_\s-]*temperature\s*[:=]\s*([^\n\r]+)",
        "fattom_oxygen": r"fattom[_\s-]*oxygen\s*[:=]\s*([^\n\r]+)",
        "fattom_moisture": r"fattom[_\s-]*moisture\s*[:=]\s*([^\n\r]+)",
    }

    risk_match = re.search(patterns["risk"], lowered, flags=re.IGNORECASE)
    confidence_match = re.search(patterns["confidence"], lowered, flags=re.IGNORECASE)
    shelf_match = re.search(patterns["shelf_life"], text, flags=re.IGNORECASE)
    storage_match = re.search(patterns["storage"], text, flags=re.IGNORECASE)
    immediate_actions_match = re.search(patterns["immediate_actions"], text, flags=re.IGNORECASE)
    warnings_match = re.search(patterns["warnings"], text, flags=re.IGNORECASE)
    fattom_food_match = re.search(patterns["fattom_food"], text, flags=re.IGNORECASE)
    fattom_acidity_match = re.search(patterns["fattom_acidity"], text, flags=re.IGNORECASE)
    fattom_time_match = re.search(patterns["fattom_time"], text, flags=re.IGNORECASE)
    fattom_temperature_match = re.search(patterns["fattom_temperature"], text, flags=re.IGNORECASE)
    fattom_oxygen_match = re.search(patterns["fattom_oxygen"], text, flags=re.IGNORECASE)
    fattom_moisture_match = re.search(patterns["fattom_moisture"], text, flags=re.IGNORECASE)

    if not all([risk_match, confidence_match, shelf_match, storage_match, immediate_actions_match, warnings_match]):
        return None
    assert risk_match is not None
    assert confidence_match is not None
    assert shelf_match is not None
    assert storage_match is not None
    assert immediate_actions_match is not None
    assert warnings_match is not None

    risk_value = str(risk_match.group(1)).strip()
    confidence_value = str(confidence_match.group(1)).strip()
    shelf_value = str(shelf_match.group(2)).strip()
    storage_value = str(storage_match.group(1)).strip()
    immediate_actions_value = str(immediate_actions_match.group(2)).strip()
    warnings_value = str(warnings_match.group(1)).strip()

    return {
        "risk": risk_value,
        "confidence": confidence_value,
        "shelf_life": shelf_value,
        "storage": storage_value,
        "immediate_actions": immediate_actions_value,
        "warnings": warnings_value,
        "fattom": {
            "food": str(fattom_food_match.group(1)).strip() if fattom_food_match else "Medium",
            "acidity": str(fattom_acidity_match.group(1)).strip() if fattom_acidity_match else "Medium",
            "time": str(fattom_time_match.group(1)).strip() if fattom_time_match else "Medium",
            "temperature": str(fattom_temperature_match.group(1)).strip() if fattom_temperature_match else "Medium",
            "oxygen": str(fattom_oxygen_match.group(1)).strip() if fattom_oxygen_match else "Low",
            "moisture": str(fattom_moisture_match.group(1)).strip() if fattom_moisture_match else "Medium",
        },
    }


def _normalize_risk(value: str) -> str:
    text = (value or "").strip().lower()
    if "high" in text:
        return "High Risk"
    if "low" in text:
        return "Low Risk"
    return "Medium Risk"


def _normalize_confidence(value: str) -> str:
    text = (value or "").strip().lower()
    if "high" in text:
        return "High Confidence"
    if "low" in text:
        return "Low Confidence"
    return "Medium Confidence"


def _has_package_state_context(value: str) -> bool:
    text = str(value or "").casefold()
    return any(
        marker in text
        for marker in (
            "unopened",
            "before opening",
            "after opening",
            "once opened",
            "opening not applicable",
            "fresh produce",
            "after preparation",
            "after cooking",
        )
    )


def _parse_profile_response(raw_text: str) -> dict | None:
    payload = _extract_json_object(raw_text)
    if not isinstance(payload, dict):
        payload = _extract_labeled_profile(raw_text)
    if not isinstance(payload, dict):
        return None

    risk = _normalize_risk(str(payload.get("risk") or ""))
    confidence = _normalize_confidence(str(payload.get("confidence") or ""))
    shelf_life = _clean_text(payload.get("shelf_life"), "5-10 days")
    storage = _clean_text(payload.get("storage"), "Store in a cool place and refrigerate after opening if needed.")
    immediate_actions = _clean_text(payload.get("immediate_actions"), "Use oldest stock first and follow package instructions.")
    warnings = _clean_text(payload.get("warnings"), "Discard if strong odor, mold, or unusual texture appears.")
    if not _has_package_state_context(shelf_life) or not _has_package_state_context(storage):
        return None

    fattom_payload = payload.get("fattom")
    risk_based_default = _default_fattom_by_risk(risk)
    if isinstance(fattom_payload, dict):
        fattom = {
            "food": _normalize_factor_level(str(fattom_payload.get("food") or ""), risk_based_default["food"]),
            "acidity": _normalize_factor_level(str(fattom_payload.get("acidity") or ""), risk_based_default["acidity"]),
            "time": _normalize_factor_level(str(fattom_payload.get("time") or ""), risk_based_default["time"]),
            "temperature": _normalize_factor_level(
                str(fattom_payload.get("temperature") or ""),
                risk_based_default["temperature"],
            ),
            "oxygen": _normalize_factor_level(str(fattom_payload.get("oxygen") or ""), risk_based_default["oxygen"]),
            "moisture": _normalize_factor_level(str(fattom_payload.get("moisture") or ""), risk_based_default["moisture"]),
        }
    else:
        fattom = {
            "food": _normalize_factor_level(str(payload.get("fattom_food") or ""), risk_based_default["food"]),
            "acidity": _normalize_factor_level(str(payload.get("fattom_acidity") or ""), risk_based_default["acidity"]),
            "time": _normalize_factor_level(str(payload.get("fattom_time") or ""), risk_based_default["time"]),
            "temperature": _normalize_factor_level(
                str(payload.get("fattom_temperature") or ""),
                risk_based_default["temperature"],
            ),
            "oxygen": _normalize_factor_level(str(payload.get("fattom_oxygen") or ""), risk_based_default["oxygen"]),
            "moisture": _normalize_factor_level(str(payload.get("fattom_moisture") or ""), risk_based_default["moisture"]),
        }

    return {
        "risk": risk,
        "confidence": confidence,
        "shelf_life": shelf_life,
        "shelf_life_days": _normalize_shelf_life_days(payload.get("shelf_life_days")),
        "storage": storage,
        "immediate_actions": immediate_actions,
        "warnings": warnings,
        "fattom": fattom,
    }


def _build_local_profile(product_name: str, categories: str) -> dict:
    """Generate a non-generic local profile when remote AI is unavailable."""

    text = f"{product_name} {categories}".lower()

    if any(word in text for word in ["milk", "yogurt", "cheese", "cream", "dairy"]):
        return {
            "risk": "High Risk",
            "confidence": "High Confidence",
            "shelf_life": "Unopened: follow the package date. After opening: use within 3-7 days.",
            "shelf_life_days": {"fresh": None, "unopened": None, "opened": 3},
            "storage": "Unopened and after opening: keep refrigerated at 1-4C; reseal tightly after opening.",
            "immediate_actions": "If unopened, refrigerate promptly. After opening, mark the date and use that container first.",
            "warnings": "Discard if sour smell, curdling, gas buildup, or visible mold appears.",
            "fattom": {
                "food": "High",
                "acidity": "Medium",
                "time": "High",
                "temperature": "High",
                "oxygen": "Medium",
                "moisture": "High",
            },
            "_provider": "local",
        }
    if any(word in text for word in ["fish", "chicken", "meat", "beef", "pork", "turkey"]):
        return {
            "risk": "High Risk",
            "confidence": "High Confidence",
            "shelf_life": "Unopened or after opening: use within 1-3 refrigerated days, or freeze sooner.",
            "shelf_life_days": {"fresh": None, "unopened": 1, "opened": 1},
            "storage": "Unopened and after opening: store in the coldest refrigerator zone; keep wrapped and cook or freeze promptly.",
            "immediate_actions": "If unopened, keep sealed until use. After opening, portion immediately and freeze what will not be cooked soon.",
            "warnings": "Discard if off-odor, slimy texture, color change, or package swelling is present.",
            "fattom": {
                "food": "High",
                "acidity": "Medium",
                "time": "High",
                "temperature": "High",
                "oxygen": "Medium",
                "moisture": "High",
            },
            "_provider": "local",
        }
    if any(word in text for word in ["frozen", "ice cream", "frozen food"]):
        return {
            "risk": "Low Risk",
            "confidence": "Medium Confidence",
            "shelf_life": "Unopened: follow the package date. After opening: use within 1-3 months for best quality.",
            "shelf_life_days": {"fresh": None, "unopened": None, "opened": 30},
            "storage": "Unopened and after opening: keep continuously frozen; reseal opened packaging and avoid thaw-refreeze cycles.",
            "immediate_actions": "If unopened, leave sealed until needed. After opening, remove one portion and return the package promptly to the freezer.",
            "warnings": "Discard if thawed for extended time, freezer-burned with off odor, or damaged packaging is found.",
            "fattom": {
                "food": "Low",
                "acidity": "Medium",
                "time": "Low",
                "temperature": "Low",
                "oxygen": "Low",
                "moisture": "Low",
            },
            "_provider": "local",
        }
    if any(word in text for word in ["bread", "bakery", "bun", "bagel", "pastry"]):
        return {
            "risk": "Medium Risk",
            "confidence": "Medium Confidence",
            "shelf_life": "Unopened: follow the package date. After opening: use within 2-5 days or freeze.",
            "shelf_life_days": {"fresh": None, "unopened": None, "opened": 2},
            "storage": "Before opening: follow the label. After opening: reseal at room temperature and freeze extra portions early.",
            "immediate_actions": "If unopened, keep the package sealed. After opening, set aside a freezer portion and use room-temperature stock first.",
            "warnings": "Discard if mold spots, fermented odor, or unusual stickiness develops.",
            "fattom": {
                "food": "Medium",
                "acidity": "Medium",
                "time": "Medium",
                "temperature": "Medium",
                "oxygen": "Medium",
                "moisture": "Low",
            },
            "_provider": "local",
        }
    if any(word in text for word in ["rice", "pasta", "grain", "cereal", "dry"]):
        return {
            "risk": "Low Risk",
            "confidence": "Medium Confidence",
            "shelf_life": "Unopened: follow the package date. After opening: use within 2-6 months for best quality.",
            "shelf_life_days": {"fresh": None, "unopened": None, "opened": 60},
            "storage": "Before opening: keep in a cool, dry cabinet. After opening: seal airtight and protect from humidity, heat, and sunlight.",
            "immediate_actions": "If unopened, leave sealed. After opening, transfer to an airtight container if the original package does not reseal.",
            "warnings": "Discard if pests, rancid odor, visible moisture damage, or clumping from spoilage is present.",
            "fattom": {
                "food": "Low",
                "acidity": "Low",
                "time": "Low",
                "temperature": "Medium",
                "oxygen": "Low",
                "moisture": "Low",
            },
            "_provider": "local",
        }
    if any(word in text for word in ["fruit", "vegetable", "produce", "salad"]):
        return {
            "risk": "Medium Risk",
            "confidence": "Medium Confidence",
            "shelf_life": "Fresh produce: use within approximately 3-10 days.",
            "shelf_life_days": {"fresh": 3, "unopened": None, "opened": None},
            "storage": "Fresh produce: keep dry and refrigerate when appropriate; use ripe items first.",
            "immediate_actions": "Fresh produce: sort it today and prepare or freeze extra ripe pieces before quality drops.",
            "warnings": "Discard pieces with mold spread, fermented odor, or slimy breakdown.",
            "fattom": {
                "food": "Medium",
                "acidity": "Medium",
                "time": "Medium",
                "temperature": "Medium",
                "oxygen": "Medium",
                "moisture": "Medium",
            },
            "_provider": "local",
        }

    return {
        "risk": "Medium Risk",
        "confidence": "Low Confidence",
        "shelf_life": "Unopened: follow the printed package date. After opening: check the label; if absent, use within 5-10 days.",
        "shelf_life_days": {"fresh": None, "unopened": None, "opened": 5},
        "storage": "Before opening: follow label storage instructions. After opening: refrigerate if required and keep tightly sealed.",
        "immediate_actions": "If unopened, check the package date. After opening, mark the open date and move the product to its labeled storage location.",
        "warnings": "Discard if package is swollen, leaking, moldy, or has unusual odor/texture.",
        "fattom": {
            "food": "Medium",
            "acidity": "Medium",
            "time": "Medium",
            "temperature": "Medium",
            "oxygen": "Low",
            "moisture": "Medium",
        },
        "_provider": "local",
    }


def fetch_ai_food_profile(product_name: str, categories: str) -> dict | None:
    """Generate profile fields from AI using product name and categories.

    Returns a dict with keys: risk, confidence, shelf_life, storage,
    immediate_actions, warnings, and fattom.
    Returns None if generation fails or output is invalid.
    """

    name = _clean_text(product_name, "Unknown food product")
    category_text = _clean_text(categories, "General packaged food")

    prompts = [
        (
            "You are a food safety assistant. Return ONLY minified JSON with keys "
            "risk,confidence,shelf_life,shelf_life_days,storage,immediate_actions,warnings,fattom. "
            "risk must be High Risk, Medium Risk, or Low Risk. "
            "confidence must be High Confidence, Medium Confidence, or Low Confidence. "
            "shelf_life must explicitly distinguish 'Unopened:' from 'After opening:'; "
            "for unpackaged fresh produce use 'Fresh produce:'. Never give an unlabeled duration. "
            "shelf_life_days must be an object with keys fresh,unopened,opened. "
            "Each value must be a conservative positive whole number of days or null when that state does not apply "
            "or no reliable duration is available. Use the lower end of a duration range. "
            "storage must explicitly distinguish 'Before opening:' from 'After opening:'; "
            "for unpackaged fresh produce use 'Fresh produce:'. "
            "immediate_actions must clearly address unopened and opened states, or fresh produce when unpackaged. "
            "warnings must be one concise food-safety warning sentence. "
            "fattom must be an object with keys food,acidity,time,temperature,oxygen,moisture. "
            "Each fattom value must be exactly one of Low, Medium, High. "
            f"Product name: {name}. Categories: {category_text}."
        ),
    ]

    last_error = ""
    for prompt in prompts:
        encoded_prompt = urllib.parse.quote(prompt, safe="")
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "PantryIQ-Connect/1.0 (github.com/kyleepinto-dot/Food-app)",
            },
        )

        # Faster response path: short network budget then local smart fallback.
        for timeout_seconds in (6, 10):
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    raw_text = response.read().decode("utf-8", errors="ignore")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
                last_error = f"network error ({type(exc).__name__})"
                continue

            parsed = _parse_profile_response(raw_text)
            if isinstance(parsed, dict):
                parsed["_provider"] = "remote"
                _set_last_error("")
                return parsed

            last_error = "AI response parse error"

    _set_last_error(last_error or "unknown error")
    return _build_local_profile(name, category_text)
