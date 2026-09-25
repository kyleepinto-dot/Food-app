"""SQLite-backed Shared Pantry screens integrated with PantryIQ Connect."""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

import flet as ft

import db  # unified multi-user data layer (schema.sql owns the tables now)
from pages.theme import ThemeColors

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pantry.db")

# Which user's pantry these functions read/write. Set once at login by main.py
# via set_current_user(); defaults to 1 so anything run before login still works.
_CURRENT_USER_ID = 1


def set_current_user(user_id) -> None:
    """main.py calls this at login so every pantry query is scoped to that user."""
    global _CURRENT_USER_ID
    _CURRENT_USER_ID = int(user_id) if user_id else 1
DEFAULT_BEST_BY_DAYS = 30
SAFETY = {
    "sealed_packaged": {"label": "Sealed", "can_donate": True},
    "fresh_produce": {"label": "Produce", "can_donate": False},
    "homemade_or_opened": {"label": "Opened", "can_donate": False},
}
FOOD_TYPES = [
    ("sealed_packaged", "Sealed & packaged"),
    ("fresh_produce", "Fresh produce"),
    ("homemade_or_opened", "Homemade / opened"),
]
LOCATIONS = ["Shelf", "Fridge", "Freezer", "Pantry", "Counter"]
UNITS = ["cans", "boxes", "bags", "jars", "bottles", "items", "lb"]


def init_pantry_db() -> None:
    """Build/upgrade the unified multi-user database (users, pantry, circles,
    shares, donations, …). db.init_db() is idempotent and migrates an older
    single-table pantry.db without losing data (existing items become owner 1)."""
    db.init_db()


def save_pantry_item(item: dict) -> int:
    """Save one validated add-form payload and return its database ID."""
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        cursor = con.execute(
            """INSERT INTO pantry_items
               (owner_id,name,best_by,qty,unit,location,notes,safety_class,status,
                added_via_scan,added_on,source_key)
               VALUES (?,?,?,?,?,?,?,?,'in_pantry',?,?,?)""",
            (
                _CURRENT_USER_ID,
                str(item.get("name") or "").strip(), str(item["best_by"]),
                max(1, int(item.get("quantity") or 1)), str(item.get("unit") or "items"),
                str(item.get("location") or "Shelf"), str(item.get("notes") or "").strip(),
                str(item.get("safety_class") or "sealed_packaged"),
                1 if item.get("added_via_scan") else 0, date.today().isoformat(),
                str(item.get("source_key") or "") or None,
            ),
        )
        return int(cursor.lastrowid)


def get_pantry_items() -> list[dict]:
    """Return active pantry rows as dictionaries, ordered by expiration."""
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM pantry_items WHERE owner_id=? AND status='in_pantry' "
            "ORDER BY best_by,id DESC", (_CURRENT_USER_ID,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_pantry_item(item_id: int) -> dict | None:
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM pantry_items WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None


def update_pantry_quantity(item_id: int, amount: int) -> None:
    """Adjust quantity and mark an item used when its quantity reaches zero."""
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        row = con.execute("SELECT qty FROM pantry_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            return
        quantity = int(row[0]) + amount
        if quantity <= 0:
            con.execute("UPDATE pantry_items SET status='used' WHERE id=?", (item_id,))
        else:
            con.execute("UPDATE pantry_items SET qty=? WHERE id=?", (quantity, item_id))


def update_pantry_note(item_id: int, note: str) -> None:
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        con.execute("UPDATE pantry_items SET notes=? WHERE id=?", (note.strip(), item_id))


def discard_pantry_item(item_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        con.execute("UPDATE pantry_items SET status='composted' WHERE id=?", (item_id,))


def _duration_days(value: str) -> int:
    text = str(value or "").lower()
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return DEFAULT_BEST_BY_DAYS
    amount = float(match.group(1))
    if "month" in text:
        amount *= 30
    elif "week" in text:
        amount *= 7
    elif "year" in text:
        amount *= 365
    return max(1, round(amount))


def scanned_product_draft(product: dict, quantity: int = 1, source_key: str = "") -> dict:
    """Translate scan/OFF metadata into the editable Shared Pantry form."""
    profile = product.get("ai_food_profile") if isinstance(product.get("ai_food_profile"), dict) else {}
    text = f"{product.get('product_name', '')} {product.get('categories', '')}".lower()
    produce_words = ("fruit", "vegetable", "produce", "salad", "apple", "banana", "tomato")
    safety = "fresh_produce" if any(word in text for word in produce_words) else "sealed_packaged"
    storage = str(profile.get("storage") or "").lower()
    location = "Freezer" if "freez" in storage else "Fridge" if "refriger" in storage or "fridge" in storage else "Shelf"
    return {
        "name": str(product.get("product_name") or product.get("generic_name") or "Unknown product").strip(),
        "best_by": (date.today() + timedelta(days=_duration_days(str(profile.get("shelf_life") or "")))).isoformat(),
        "quantity": max(1, int(quantity)), "unit": "items", "location": location,
        "notes": "", "safety_class": safety, "added_via_scan": True,
        "source_key": source_key,
    }


def manual_pantry_draft() -> dict:
    return {
        "name": "", "best_by": (date.today() + timedelta(days=DEFAULT_BEST_BY_DAYS)).isoformat(),
        "quantity": 1, "unit": "items", "location": "Shelf", "notes": "",
        "safety_class": "sealed_packaged", "added_via_scan": False, "source_key": "",
    }


def pantry_items_for_meals(items: list[dict] | None = None) -> list[dict]:
    """Convert database rows to the existing meal-planner inventory contract."""
    inventory = []
    for item in items if items is not None else get_pantry_items():
        best_by = date.fromisoformat(str(item["best_by"]))
        added_on = date.fromisoformat(str(item["added_on"]))
        remaining = max(0, (best_by - date.today()).days)
        inventory.append({
            "key": f"pantry:{item['id']}", "name": str(item.get("name") or "Food item"),
            "category": SAFETY.get(str(item.get("safety_class")), SAFETY["sealed_packaged"])["label"],
            "quantity": int(item.get("qty") or 1),
            "freshness": "Use today" if remaining == 0 else f"{remaining} days left",
            "storage": str(item.get("location") or "Pantry"),
            "added_at": datetime.combine(added_on, datetime.min.time(), timezone.utc).isoformat(),
            "shelf_life": f"{max(1, (best_by - added_on).days)} days",
            "risk": "High Risk" if remaining <= 2 else "Medium Risk" if remaining <= 7 else "Low Risk",
        })
    return inventory


def build_nav_item(
    icon: ft.IconData,
    label: str,
    selected: bool = False,
    compact: bool = False,
) -> ft.Column:
    """Return a bottom navigation item shared with the meal planner."""

    color = ThemeColors.GREEN_TEXT if selected else ThemeColors.TEXT_INACTIVE
    controls: list[ft.Control] = [ft.Icon(icon, color=color, size=24)]
    if not compact:
        controls.append(ft.Text(label, size=12, color=color, weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500))
    return ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=controls)


def _shell(metrics: dict, controls: list[ft.Control], on_home, on_scan, on_me) -> ft.Container:
    compact = metrics["shell_width"] < 360
    bottom = ft.Container(
        left=0, right=0, bottom=0, bgcolor="#FFFFFF",
        padding=ft.Padding(left=12, top=8, right=12, bottom=10),
        content=ft.Column(spacing=6, controls=[
            ft.Divider(height=1, color=ThemeColors.DIVIDER),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[
                ft.GestureDetector(on_tap=on_home, content=build_nav_item(ft.Icons.HOME_ROUNDED, "Dashboard", False, compact)),
                ft.GestureDetector(on_tap=on_scan, content=build_nav_item(ft.Icons.CAMERA_ALT_OUTLINED, "Scan Food", False, compact)),
                build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", True, compact),
                ft.GestureDetector(on_tap=on_me, content=build_nav_item(ft.Icons.PERSON_OUTLINE, "Me", False, compact)),
            ]),
        ]),
    )
    return ft.Container(
        width=metrics["shell_width"], height=metrics["shell_height"],
        bgcolor=ThemeColors.GREEN_SURFACE, border_radius=34,
        padding=ft.Padding(left=14, top=16, right=14, bottom=0),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=30, color=ThemeColors.SHELL_SHADOW, offset=ft.Offset(0, 8)),
        content=ft.Stack(controls=[
            ft.Column(spacing=ThemeColors.SECTION_SPACING, scroll=ft.ScrollMode.AUTO, controls=controls + [ft.Container(height=82)]),
            bottom,
        ]),
    )


def _header(metrics: dict, subtitle: str, on_back=None) -> ft.Container:
    return ft.Container(
        bgcolor="#FFFFFF", border_radius=26, padding=ft.Padding(left=12, top=10, right=12, bottom=10),
        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, on_click=on_back) if on_back else ft.Container(width=40),
            ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text("PantryIQ Connect", size=24 if metrics["is_desktop"] else 18, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
                ft.Text(subtitle, size=14, color=ThemeColors.TEXT_SECONDARY, weight=ft.FontWeight.W_600),
            ]),
            ft.Icon(ft.Icons.GROUP_OUTLINED, color=ThemeColors.GREEN_TEXT, size=26),
        ]),
    )


def _urgency(best_by: str) -> tuple[int, str, str, str]:
    days = (date.fromisoformat(best_by) - date.today()).days
    if days < 0:
        return days, "Expired", "#FBE9E5", "#B5402C"
    if days == 0:
        return days, "Use today", "#FBE9E5", "#B5402C"
    if days <= 2:
        return days, f"{days} days left", "#FBE9E5", "#B5402C"
    if days <= 7:
        return days, f"{days} days left", "#F7E9C8", "#8F6410"
    return days, f"{days} days left", "#E7F0E0", ThemeColors.GREEN_TEXT


def build_pantry_shell(
    metrics: dict, on_home_click, on_scan_click, on_me_click,
    on_meal_planner_click, on_dummy_meal_planner_click,
    pantry_products: list[dict], on_quantity_change, on_add_manual_click,
    on_item_options_click, selected_filter: str = "Expiring first", on_filter_change=None,
) -> ft.Container:
    """Render the persistent Shared Pantry, replacing the old in-memory page."""
    all_items = [item for item in pantry_products if isinstance(item, dict)]
    items = [item for item in all_items if item.get("location") == selected_filter] if selected_filter in LOCATIONS else all_items
    total = sum(int(item.get("qty") or 0) for item in all_items)

    def filter_chip(name: str) -> ft.Container:
        active = name == selected_filter
        return ft.Container(
            bgcolor=ThemeColors.GREEN_TEXT if active else "#F1F4F0", border_radius=20,
            padding=ft.Padding(left=12, top=6, right=12, bottom=6),
            on_click=(lambda _, value=name: on_filter_change(value)) if on_filter_change else None,
            content=ft.Text(name, size=12, color="#FFFFFF" if active else ThemeColors.TEXT_SECONDARY, weight=ft.FontWeight.BOLD),
        )

    rows: list[ft.Control] = []
    for item in items:
        item_id = int(item["id"])
        days, expiry, tint, strong = _urgency(str(item["best_by"]))
        safety = SAFETY.get(str(item.get("safety_class")), SAFETY["sealed_packaged"])
        rows.append(ft.Container(
            bgcolor="#FFFFFF", border_radius=16, padding=12,
            border=ft.Border.all(1.5 if days <= 7 else 1, strong if days <= 7 else "#E1E7E2"),
            content=ft.Column(spacing=7, controls=[
                ft.Row(vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                    ft.Column(expand=True, spacing=3, controls=[
                        ft.Text(str(item.get("name") or "Food item"), size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{item.get('location')} · {safety['label']} · best by {item.get('best_by')}", size=12, color=ThemeColors.TEXT_SECONDARY),
                        ft.Text(str(item.get("notes")), size=12, color="#8F6410") if item.get("notes") else ft.Container(),
                    ]),
                    ft.Container(bgcolor=tint, border_radius=20, padding=7, content=ft.Text(expiry, size=11, color=strong, weight=ft.FontWeight.BOLD)),
                ]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Row(tight=True, spacing=1, controls=[
                        ft.IconButton(ft.Icons.REMOVE, icon_size=17, on_click=lambda _, value=item_id: on_quantity_change(value, -1)),
                        ft.Text(f"{item.get('qty')} {item.get('unit')}", size=13, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.ADD, icon_size=17, on_click=lambda _, value=item_id: on_quantity_change(value, 1)),
                    ]),
                    ft.Button(content=ft.Text("Options", size=12), on_click=lambda _, value=item_id: on_item_options_click(value),
                              style=ft.ButtonStyle(bgcolor="#E7F0E0", color=ThemeColors.GREEN_TEXT, shape=ft.RoundedRectangleBorder(radius=12))),
                ]),
            ]),
        ))
    if not rows:
        rows.append(ft.Container(
            bgcolor="#FFFFFF", border_radius=16, padding=22, alignment=ft.Alignment(0, 0),
            content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text("🥫", size=34), ft.Text("No Shared Pantry items yet", weight=ft.FontWeight.BOLD),
                ft.Text("Scan a product or add one manually.", size=13, color=ThemeColors.TEXT_SECONDARY),
            ]),
        ))

    controls = [
        _header(metrics, "Shared Pantry"),
        ft.Container(bgcolor="#DFEBDD", border_radius=18, padding=16, content=ft.Column(spacing=10, controls=[
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Column(expand=True, spacing=3, controls=[
                    ft.Text("Your Shared Pantry", size=26 if metrics["is_desktop"] else 21, weight=ft.FontWeight.BOLD),
                    ft.Text("Use, share, or donate food before it expires.", size=13, color=ThemeColors.TEXT_SECONDARY),
                ]),
                ft.Container(bgcolor="#FFFFFF", border_radius=12, padding=9, content=ft.Text(f"{total} items", weight=ft.FontWeight.BOLD)),
            ]),
            ft.Row(spacing=8, controls=[
                ft.Button(expand=True, content=ft.Text("Scan to add", weight=ft.FontWeight.BOLD), on_click=on_scan_click,
                          style=ft.ButtonStyle(bgcolor=ThemeColors.BRAND_PRIMARY, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=13))),
                ft.Button(expand=True, content=ft.Text("Add manually", weight=ft.FontWeight.BOLD), on_click=on_add_manual_click,
                          style=ft.ButtonStyle(bgcolor="#FFFFFF", color=ThemeColors.GREEN_TEXT, shape=ft.RoundedRectangleBorder(radius=13))),
            ]),
        ])),
        ft.Row(wrap=True, spacing=6, run_spacing=6, controls=[filter_chip(value) for value in ["Expiring first", "All", "Fridge", "Freezer", "Shelf"]]),
        ft.Column(spacing=9, controls=rows),
        ft.Row(spacing=8, controls=[
            ft.Button(expand=True, content=ft.Text("Meal Planner"), on_click=on_meal_planner_click,
                      style=ft.ButtonStyle(bgcolor=ThemeColors.BRAND_PRIMARY, color="#FFFFFF")),
            ft.Button(expand=True, content=ft.Text("Demo Planner"), on_click=on_dummy_meal_planner_click,
                      style=ft.ButtonStyle(bgcolor="#FFFFFF", color=ThemeColors.GREEN_TEXT)),
        ]),
        ft.Container(bgcolor="#F7E9C8", border_radius=14, padding=12,
                     content=ft.Text("💡 Sealed, in-date food can be donated. Produce can be shared; opened or homemade food should only be shared with your circle.", size=12, color="#7A570E")),
    ]
    return _shell(metrics, controls, on_home_click, on_scan_click, on_me_click)


def build_add_pantry_shell(metrics: dict, draft: dict, on_save, on_cancel, on_home_click, on_scan_click, on_me_click) -> ft.Container:
    """Render one shared add form, prefilled when opened from scan results."""
    name = ft.TextField(value=str(draft.get("name") or ""), label="Item name", border_radius=12)
    best_by = ft.TextField(value=str(draft.get("best_by") or ""), label="Best-by date (YYYY-MM-DD)", border_radius=12)
    quantity = ft.TextField(value=str(draft.get("quantity") or 1), label="Quantity", keyboard_type=ft.KeyboardType.NUMBER, border_radius=12, expand=True)
    unit = ft.Dropdown(value=str(draft.get("unit") or "items"), label="Unit", options=[ft.dropdown.Option(key=v, text=v) for v in UNITS], border_radius=12, expand=True)
    location = ft.Dropdown(value=str(draft.get("location") or "Shelf"), label="Location", options=[ft.dropdown.Option(key=v, text=v) for v in LOCATIONS], border_radius=12, expand=True)
    safety = ft.Dropdown(value=str(draft.get("safety_class") or "sealed_packaged"), label="Food type", options=[ft.dropdown.Option(key=k, text=v) for k, v in FOOD_TYPES], border_radius=12, expand=True)
    notes = ft.TextField(value=str(draft.get("notes") or ""), label="Note for the family", multiline=True, min_lines=2, max_lines=3, border_radius=12)

    def submit(_):
        if not str(name.value or "").strip():
            name.error_text = "Enter an item name"; name.update(); return
        try:
            parsed_date = date.fromisoformat(str(best_by.value or "").strip())
        except ValueError:
            best_by.error_text = "Use YYYY-MM-DD"; best_by.update(); return
        try:
            parsed_quantity = int(str(quantity.value or "").strip())
            if parsed_quantity <= 0:
                raise ValueError
        except ValueError:
            quantity.error_text = "Enter a positive number"; quantity.update(); return
        on_save({**draft, "name": str(name.value).strip(), "best_by": parsed_date.isoformat(),
                 "quantity": parsed_quantity, "unit": str(unit.value or "items"),
                 "location": str(location.value or "Shelf"), "safety_class": str(safety.value or "sealed_packaged"),
                 "notes": str(notes.value or "").strip()})

    source = "Review the scanned details before saving." if draft.get("added_via_scan") else "Enter an item to share with your household."
    controls = [
        _header(metrics, "Add to Shared Pantry", on_cancel),
        ft.Container(bgcolor="#FFFFFF", border_radius=18, padding=16, content=ft.Column(spacing=12, controls=[
            ft.Text("Add to Shared Pantry", size=22, weight=ft.FontWeight.BOLD), ft.Text(source, size=13, color=ThemeColors.TEXT_SECONDARY),
            name, ft.Row(spacing=8, controls=[safety, location]), best_by,
            ft.Row(spacing=8, controls=[quantity, unit]), notes,
            ft.Row(alignment=ft.MainAxisAlignment.END, controls=[
                ft.Button(content=ft.Text("Cancel"), on_click=on_cancel, style=ft.ButtonStyle(bgcolor="#EEF1EE")),
                ft.Button(content=ft.Text("Save to Shared Pantry"), on_click=submit, style=ft.ButtonStyle(bgcolor=ThemeColors.BRAND_PRIMARY, color="#FFFFFF")),
            ]),
        ])),
    ]
    return _shell(metrics, controls, on_home_click, on_scan_click, on_me_click)


def build_pantry_item_options_shell(
    metrics: dict, item: dict, on_back_click, on_save_note, on_discard,
    on_use, on_share, on_donate, on_home_click, on_scan_click, on_me_click,
) -> ft.Container:
    """Render food-safety-aware actions and note editing for one item."""
    safety_key = str(item.get("safety_class") or "sealed_packaged")
    safety = SAFETY.get(safety_key, SAFETY["sealed_packaged"])
    days, expiry, tint, strong = _urgency(str(item["best_by"]))
    notes = ft.TextField(value=str(item.get("notes") or ""), label="Family note", multiline=True, min_lines=2, max_lines=4, border_radius=12)
    outline = ft.ButtonStyle(bgcolor="#FFFFFF", color=ThemeColors.GREEN_TEXT, side=ft.BorderSide(1, ThemeColors.BRAND_PRIMARY), shape=ft.RoundedRectangleBorder(radius=13))
    share_label = "Share with my Circle" if safety_key == "homemade_or_opened" else "Share food"
    eligible = bool(safety["can_donate"] and days >= 0)
    controls = [
        _header(metrics, "Item Options", on_back_click),
        ft.Container(bgcolor="#FFFFFF", border_radius=18, padding=16, content=ft.Column(spacing=10, controls=[
            ft.Row(controls=[
                ft.Column(expand=True, spacing=4, controls=[
                    ft.Text(str(item.get("name") or "Food item"), size=23, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{item.get('qty')} {item.get('unit')} · {item.get('location')} · {safety['label']}", color=ThemeColors.TEXT_SECONDARY),
                ]),
                ft.Container(bgcolor=tint, border_radius=20, padding=8, content=ft.Text(expiry, color=strong, weight=ft.FontWeight.BOLD, size=12)),
            ]),
            ft.Divider(color=ThemeColors.DIVIDER), ft.Text("What do you want to do with it?", weight=ft.FontWeight.BOLD),
            ft.Button(content=ft.Text("🍳 Use it — see recipes"), on_click=on_use, style=ft.ButtonStyle(bgcolor=ThemeColors.BRAND_PRIMARY, color="#FFFFFF")),
            ft.Button(content=ft.Text(f"🤝 {share_label}"), on_click=lambda _: on_share(item), style=outline),
            ft.Button(content=ft.Text("🏦 Donate to a food bank" if eligible else "🏦 Not eligible for donation"),
                      on_click=(lambda _: on_donate(item)) if eligible else None, disabled=not eligible, style=outline),
            ft.Button(content=ft.Text("🌱 Compost / discard"), on_click=lambda _: on_discard(int(item["id"])),
                      style=ft.ButtonStyle(bgcolor="#FFF7E5", color="#8F6410")),
            ft.Divider(color=ThemeColors.DIVIDER), notes,
            ft.Button(content=ft.Text("Save note"), on_click=lambda _: on_save_note(int(item["id"]), str(notes.value or "")), style=outline),
        ])),
    ]
    return _shell(metrics, controls, on_home_click, on_scan_click, on_me_click)
