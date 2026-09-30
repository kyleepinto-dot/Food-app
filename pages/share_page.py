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

from datetime import date

import flet as ft

import dates
from pages.theme import ThemeColors as T
from pages.shell_kit import app_shell, app_header

SHARE_TYPES = [
    ("homemade_or_opened", "Homemade / opened"),
    ("sealed_packaged", "Sealed & packaged"),
    ("fresh_produce", "Fresh produce (uncut)"),
]
TYPE_LABEL = {k: v for k, v in SHARE_TYPES}


def _time_options() -> list[str]:
    """Pickup times every 30 min from 7:00 AM to 9:30 PM, with AM/PM."""
    out = []
    for h24 in range(7, 22):
        for minute in (0, 30):
            ampm = "AM" if h24 < 12 else "PM"
            h12 = h24 % 12 or 12
            out.append(f"{h12}:{minute:02d} {ampm}")
    return out


TIME_OPTIONS = _time_options()

# Words that hint an item is a prepared/cooked dish (so "Sealed & packaged" is
# probably wrong). Used only for a soft nudge — the attestation checkbox is the
# real gate, so a false match just shows a slightly different message.
COOKED_WORDS = (
    "bake", "baked", "soup", "stew", "curry", "casserole", "roast", "roasted",
    "fried", "grilled", "cooked", "homemade", "home-made", "leftover", "leftovers",
    "lasagna", "meatball", "burrito", "taco", "chili", "stir fry", "stir-fry",
    "gravy", "sauce", "stuffing", "quiche", "risotto",
)


def _looks_cooked(name: str) -> bool:
    low = (name or "").lower()
    return any(word in low for word in COOKED_WORDS)


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
    locked_best_by_iso = str(draft.get("best_by") or "")  # the item's stored date (ISO)
    best_by_in = ft.TextField(
        value=dates.iso_to_mdy(locked_best_by_iso),
        label="Best-by date (from your pantry item)" if locked else "Best-by date (MM-DD-YYYY)",
        hint_text="e.g. 10-15-2026",
        read_only=locked, disabled=locked,
        border_radius=12, border_color="#D8D4C6", focused_border_color=T.BRAND_PRIMARY,
    )
    pickup_date_in = ft.TextField(
        label="Pickup date (MM-DD-YYYY)", hint_text="e.g. 10-05-2026",
        border_radius=12, border_color="#D8D4C6", focused_border_color=T.BRAND_PRIMARY, expand=True,
    )
    pickup_time_dd = ft.Dropdown(
        label="Pickup time", border_radius=12, expand=True,
        options=[ft.dropdown.Option(t) for t in TIME_OPTIONS],
    )
    err = ft.Text("", size=13, color="#B5402C", visible=False)

    def _show_err(msg: str) -> None:
        err.value = msg
        err.visible = True
        err.update()

    def _reformat(field):
        parsed = dates.parse_mdy(field.value)
        if parsed:
            field.value = parsed.strftime("%m-%d-%Y")
            field.update()
    if not locked:
        best_by_in.on_blur = lambda _: _reformat(best_by_in)
    pickup_date_in.on_blur = lambda _: _reformat(pickup_date_in)

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

    # Attestation: required only for the widest audience (sealed -> food banks).
    # Shown for locked sealed items, or always for a free share (type can change).
    show_attest = (default_safety == "sealed_packaged") if locked else True
    attest = ft.Checkbox(
        value=False, active_color=T.BRAND_PRIMARY,
        label="I confirm this is sealed, unopened, and in-date (required to offer it to the community or food banks).",
    ) if show_attest else None

    def submit(_):
        title = str(title_in.value or "").strip()
        if not title:
            _show_err("Give it a name & quantity first.")
            return
        # Wider-audience (sealed) shares need the confirmation ticked; nudge if the
        # name looks like a cooked dish that probably shouldn't be marked sealed.
        if get_safety() == "sealed_packaged" and (attest is None or not attest.value):
            if _looks_cooked(title):
                _show_err(f"\"{title}\" looks like a prepared dish. If it's truly sealed & "
                          f"packaged, tick the confirmation box below to continue.")
            else:
                _show_err("Please tick the box confirming this is sealed, unopened & in-date "
                          "to offer it to the community or food banks.")
            return
        # Best-by: a locked share uses the item's stored date; a free share parses the field.
        if locked:
            best_by_iso = locked_best_by_iso
        else:
            raw = str(best_by_in.value or "").strip()
            best_by_iso = ""
            if raw:
                d = dates.parse_mdy(raw)
                if d is None:
                    _show_err("Best-by date must look like 10-15-2026.")
                    return
                if d < date.today():
                    _show_err("Best-by date can't be in the past.")
                    return
                best_by_iso = d.isoformat()
        pdate = ""
        pdate_raw = str(pickup_date_in.value or "").strip()
        if pdate_raw:
            d = dates.parse_mdy(pdate_raw)
            if d is None:
                _show_err("Pickup date must be a real date like 10-05-2026.")
                return
            if d < date.today():
                _show_err("Pickup date can't be in the past.")
                return
            if best_by_iso and d > date.fromisoformat(best_by_iso):
                _show_err("Pickup date must be on or before the best-by date, or the food will be past its best-by.")
                return
            pdate = d.strftime("%m-%d-%Y")   # auto-formatted to MM-DD-YYYY
        ptime = str(pickup_time_dd.value or "").strip()
        if pdate and ptime:
            pickup_window = f"{pdate} at {ptime}"
        elif pdate:
            pickup_window = pdate
        elif ptime:
            pickup_window = ptime
        else:
            pickup_window = "Flexible - arrange together"
        on_share({
            "title": title, "safety_class": get_safety(),
            "best_by": best_by_iso, "pickup_window": pickup_window,
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
            best_by_in,
            ft.Text("When can they pick it up?", size=13, weight=ft.FontWeight.BOLD, color=T.TEXT_SECONDARY),
            ft.Row(spacing=8, controls=[pickup_date_in, pickup_time_dd]),
            *([attest] if attest else []),
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


def build_my_shares_shell(
    metrics: dict, shares: list, on_back,
    on_home_click, on_scan_click, on_pantry_click, on_me_click,
) -> ft.Container:
    """List the food this user has posted to share, with who can see each item."""
    cards = []
    for s in shares:
        safety = str(s.get("safety_class") or "homemade_or_opened")
        status = str(s.get("status") or "available")
        cards.append(ft.Container(
            bgcolor="#FFFFFF", border=ft.Border.all(1, "#E1E7E2"), border_radius=16, padding=14,
            content=ft.Column(spacing=6, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                    ft.Text(str(s.get("title") or "Shared item"), size=15, weight=ft.FontWeight.BOLD,
                            color=T.TEXT_PRIMARY, expand=True),
                    ft.Container(bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
                                 padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                                 content=ft.Text(status.replace("_", " "), size=11, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT)),
                ]),
                ft.Text(f"👀 Who can see it: {audience_text(safety)}", size=13, color=T.TEXT_SECONDARY),
                ft.Text(f"🕒 Pickup: {s.get('pickup_window') or 'flexible'}", size=13, color=T.TEXT_SECONDARY),
                ft.Text(f"Shared on {s.get('created_on') or ''}", size=12, color=T.TEXT_INACTIVE),
            ]),
        ))
    if not cards:
        cards = [ft.Container(
            bgcolor="#FFFFFF", border_radius=16, padding=22, alignment=ft.Alignment(0, 0),
            content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, controls=[
                ft.Text("🤝", size=34),
                ft.Text("You haven't shared anything yet", weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                ft.Text("Share a pantry item and it'll show up here.", size=13, color=T.TEXT_SECONDARY),
            ]),
        )]
    controls = [
        app_header(metrics, "My Shares", on_back),
        ft.Text("Food you've offered to share, and who can see each one.", size=13, color=T.TEXT_SECONDARY),
        *cards,
    ]
    return app_shell(metrics, controls, "me", on_home_click, on_scan_click, on_pantry_click, on_me_click)
