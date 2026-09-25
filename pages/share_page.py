"""Share screen for PantryIQ Connect (ported from Yaashvi's app).

The Share form posts food to the right audience, decided by the food-safety type:
  homemade/opened -> My Circle only
  fresh produce   -> My Circle + Community
  sealed/packaged -> My Circle + Community + Food banks
When sharing straight from a pantry item, the type is LOCKED to that item's type
so the audience can never be broadened (rule enforced in db.create_share).

Flet 0.85, shared shell, UI only. main.py handles the actual db.create_share call
inside the on_share callback.

Data contract:
  draft = {"locked": bool, "title": str, "safety_class": str}
Callback:
  on_share({"title", "safety_class", "best_by", "pickup_window"})
"""

from __future__ import annotations

import flet as ft

from pages.theme import ThemeColors as T
from pages.shell_kit import app_shell, app_header

SHARE_TYPES = [
    ("homemade_or_opened", "Homemade / opened"),
    ("sealed_packaged", "Sealed & packaged"),
    ("fresh_produce", "Fresh produce (uncut)"),
]
TYPE_LABEL = {k: v for k, v in SHARE_TYPES}
BEST_BY_OPTIONS = ["Made today", "Best by this week", "Best by next week", "Best by this month"]
PICKUP_OPTIONS = ["Today 5–7pm", "Tomorrow morning", "This weekend", "Anytime — message me"]


def audience_text(safety_class: str) -> str:
    """Friendly words for who can see a share of this food type."""
    scopes = {
        "sealed_packaged": ["circle", "community", "food_bank"],
        "fresh_produce": ["circle", "community"],
    }.get(safety_class, ["circle"])
    names = {"circle": "My Circle", "community": "Community", "food_bank": "Food banks"}
    if scopes == ["circle"]:
        return "visible only to My Circle"
    return " + ".join(names[s] for s in scopes)


def build_share_shell(
    metrics: dict, draft: dict, on_share, on_cancel,
    on_home_click, on_scan_click, on_pantry_click, on_me_click, on_back_click=None,
) -> ft.Container:
    """Render the Share form. UI only; main.py posts the share in on_share."""
    locked = bool(draft.get("locked"))
    default_safety = str(draft.get("safety_class") or "homemade_or_opened")

    title_in = ft.TextField(
        value=str(draft.get("title") or ""),
        label="Name & quantity — e.g. Veggie pasta bake, serves 4",
        border_radius=12, border_color="#D8D4C6", focused_border_color=T.BRAND_PRIMARY,
    )
    best_by_dd = ft.Dropdown(
        label="Made / best-by date", border_radius=12, expand=True,
        options=[ft.dropdown.Option(x) for x in BEST_BY_OPTIONS],
    )
    pickup_dd = ft.Dropdown(
        label="Pickup window", border_radius=12, expand=True,
        options=[ft.dropdown.Option(x) for x in PICKUP_OPTIONS],
    )
    err = ft.Text("", size=13, color="#B5402C", visible=False)

    # Food-type chooser: locked note (from a pantry item) or radios (free share).
    if locked:
        get_safety = lambda: default_safety
        type_inner = ft.Container(
            bgcolor="#FAF7EC", border=ft.Border.all(1, "#E6D5A8"), border_radius=12,
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            content=ft.Text(
                f"Locked to this item: {TYPE_LABEL.get(default_safety, default_safety)}  →  "
                f"{audience_text(default_safety)}. Food-safety rules set the audience — "
                f"you can't broaden it.",
                size=13, color="#8F6410"),
        )
    else:
        radio = ft.RadioGroup(
            value=default_safety,
            content=ft.Column(spacing=6, controls=[
                ft.Radio(value=k, label=f"{lbl}   →   {audience_text(k)}", active_color=T.BRAND_PRIMARY)
                for k, lbl in SHARE_TYPES
            ]),
        )
        get_safety = lambda: radio.value
        type_inner = radio

    def submit(_):
        title = str(title_in.value or "").strip()
        if not title:
            err.value = "Give it a name & quantity first."
            err.visible = True
            err.update()
            return
        on_share({
            "title": title, "safety_class": get_safety(),
            "best_by": best_by_dd.value, "pickup_window": pickup_dd.value,
        })

    controls = [
        app_header(metrics, "Share food", on_back_click),
        ft.Container(bgcolor="#DFEBDD", border_radius=18, padding=16, content=ft.Column(spacing=4, controls=[
            ft.Text("Share food", size=22, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            ft.Text("What you share and who can see it depends on food-safety rules — we handle that for you.",
                    size=13, color=T.TEXT_SECONDARY),
        ])),
        ft.Container(bgcolor="#FFFFFF", border_radius=18, padding=16, content=ft.Column(spacing=10, controls=[
            ft.Text("What kind of food is it?", size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            type_inner,
        ])),
        ft.Container(bgcolor="#FFFFFF", border_radius=18, padding=16, content=ft.Column(spacing=12, controls=[
            title_in,
            ft.Row(spacing=8, controls=[best_by_dd, pickup_dd]),
        ])),
        err,
        ft.Row(spacing=8, controls=[
            ft.Button(expand=True, content=ft.Text("Cancel"), on_click=on_cancel,
                      style=ft.ButtonStyle(bgcolor="#EEF1EE", color=T.GREEN_TEXT,
                                           shape=ft.RoundedRectangleBorder(radius=13))),
            ft.Button(expand=True, content=ft.Text("Share it", weight=ft.FontWeight.BOLD), on_click=submit,
                      style=ft.ButtonStyle(bgcolor=T.BRAND_PRIMARY, color="#FFFFFF",
                                           shape=ft.RoundedRectangleBorder(radius=13))),
        ]),
    ]
    return app_shell(metrics, controls, "me", on_home_click, on_scan_click, on_pantry_click, on_me_click)
