"""
SharedPantry — Yaashvi's screens (Milestones M5–M7)
===================================================

A COMPLETE, working Flet (Python) app. Starts with an EMPTY pantry — there is
NO fake/demo data anywhere. Everything you see is something you added.

Screens included:
  * Shared Pantry list  — your items, sorted expiring-first, with filters,
    colored shelf-life bars, and a days-left countdown that updates daily.
  * Add to Pantry       — reached by "Add manually" (type it yourself) or, later,
    by Kylee's scanner (which will pre-fill this same form). You set: item name,
    food type (sealed / produce / homemade — this drives the safety rules),
    best-by date, quantity, location, and a family note.
  * Item Options        — Use / Share / Donate (only for sealed items) /
    Compost-discard / Add-edit note.
  * Achievements        — real stats + badges based on what you've actually done.

Items are saved in a SQLite file called  pantry.db  (created automatically next
to this file). Delete pantry.db anytime to start over with an empty pantry.

How to run it (in VS Code):
  1. Install Flet once:            pip install flet
  2. In the terminal, run:         python main.py
     (A desktop window opens. You can also run:  flet run )

Colors and fonts follow the team's design handoff so it matches the rest of the app.
"""

import os
import sqlite3
import threading
import time
from datetime import date, timedelta

import flet as ft

# ---------------------------------------------------------------------------
# Design tokens (from design_handoff_sharedpantry/README.md)
# ---------------------------------------------------------------------------
BG          = "#F6F4EE"   # page background
CARD        = "#FFFFFF"   # card background
CARD_BORDER = "#E3E0D5"   # card border
GREEN       = "#1E5B3C"   # primary green
GREEN_DARK  = "#1C4030"   # dark green text
GREEN_TINT  = "#E7F0E0"   # green tint / "ok" chip
BODY        = "#23281F"   # body text
SECONDARY   = "#6B7263"   # secondary text
INPUT_BORDER = "#D8D4C6"  # input border
TRACK       = "#EFEDE5"   # slider/progress track

RADIUS_CARD  = 14
RADIUS_INPUT = 10

# Starting values for a blank "Add to Pantry" form. (In the finished app the
# scanner can pre-fill these, but the user can always type/adjust them here.)
DEFAULT_BEST_BY_DAYS = 30    # slider starts 30 days out

# Food-safety classes drive which actions are allowed on an item.
#   sealed_packaged   -> Share + Donate (Circle, Community, food banks)
#   fresh_produce     -> Share only (Circle + Community, no donation)
#   homemade_or_opened-> Share to Circle only, never donated
SAFETY = {
    "sealed_packaged":   {"label": "Sealed",   "can_donate": True},
    "fresh_produce":     {"label": "Produce",  "can_donate": False},
    "homemade_or_opened":{"label": "Opened",   "can_donate": False},
}

# The choices shown in the "Food type" dropdown -> which safety class each maps to.
FOOD_TYPES = [
    ("sealed_packaged",    "Sealed & packaged"),
    ("fresh_produce",      "Fresh produce"),
    ("homemade_or_opened", "Homemade / opened"),
]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pantry.db")


# ---------------------------------------------------------------------------
# Tiny database layer (matches the pantry_items table from the README)
# ---------------------------------------------------------------------------
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS pantry_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            best_by     TEXT NOT NULL,      -- YYYY-MM-DD
            qty         INTEGER NOT NULL,
            unit        TEXT NOT NULL,
            location    TEXT NOT NULL,
            notes       TEXT,
            safety_class TEXT DEFAULT 'sealed_packaged',
            status      TEXT DEFAULT 'in_pantry',
            added_via_scan INTEGER DEFAULT 1,
            added_on    TEXT NOT NULL       -- YYYY-MM-DD
        )
        """
    )
    # Migration: if an older pantry.db exists without safety_class, add it.
    cols = [r[1] for r in con.execute("PRAGMA table_info(pantry_items)").fetchall()]
    if "safety_class" not in cols:
        con.execute("ALTER TABLE pantry_items ADD COLUMN safety_class TEXT DEFAULT 'sealed_packaged'")
    con.commit()
    con.close()


def save_item(name, best_by, qty, unit, location, notes,
              safety_class="sealed_packaged", added_on=None):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO pantry_items
           (name, best_by, qty, unit, location, notes, safety_class, added_on)
           VALUES (?,?,?,?,?,?,?,?)""",
        (name, best_by.isoformat(), qty, unit, location, notes, safety_class,
         (added_on or date.today()).isoformat()),
    )
    con.commit()
    con.close()


def get_items():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM pantry_items WHERE status = 'in_pantry' ORDER BY best_by ASC"
    ).fetchall()
    con.close()
    return rows


def get_item(item_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM pantry_items WHERE id = ?", (item_id,)).fetchone()
    con.close()
    return row


def update_note(item_id, note):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE pantry_items SET notes = ? WHERE id = ?", (note, item_id))
    con.commit()
    con.close()


def discard_item(item_id):
    """Mark an item as composted/discarded so it leaves the pantry list."""
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE pantry_items SET status = 'composted' WHERE id = ?", (item_id,))
    con.commit()
    con.close()


def get_stats():
    """Real counts from the database — used by the Achievements page."""
    con = sqlite3.connect(DB_PATH)
    total     = con.execute("SELECT COUNT(*) FROM pantry_items").fetchone()[0]
    in_pantry = con.execute("SELECT COUNT(*) FROM pantry_items WHERE status='in_pantry'").fetchone()[0]
    composted = con.execute("SELECT COUNT(*) FROM pantry_items WHERE status='composted'").fetchone()[0]
    con.close()
    return {"total": total, "in_pantry": in_pantry, "composted": composted}


# ---------------------------------------------------------------------------
# Small reusable UI helpers so the styling matches the design system
# ---------------------------------------------------------------------------
def card(content, padding=18):
    return ft.Container(
        content=content,
        bgcolor=CARD,
        border=ft.border.all(1, CARD_BORDER),
        border_radius=RADIUS_CARD,
        padding=padding,
    )


def chip(text, bg=GREEN_TINT, color=GREEN_DARK):
    return ft.Container(
        content=ft.Text(text, size=12.5, weight=ft.FontWeight.BOLD, color=color),
        bgcolor=bg,
        border_radius=999,
        padding=ft.Padding(12, 4, 12, 4),
    )


def field_label(text):
    return ft.Text(text, size=14, weight=ft.FontWeight.BOLD, color=BODY)


def primary_button(text, on_click):
    return ft.FilledButton(
        content=ft.Text(text, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=GREEN,
            shape=ft.RoundedRectangleBorder(radius=RADIUS_INPUT),
            padding=ft.Padding(18, 12, 18, 12),
        ),
    )


def secondary_button(text, on_click):
    return ft.OutlinedButton(
        content=ft.Text(text, weight=ft.FontWeight.BOLD, color=GREEN_DARK),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=CARD,
            side=ft.BorderSide(1.5, GREEN),
            shape=ft.RoundedRectangleBorder(radius=RADIUS_INPUT),
            padding=ft.Padding(16, 11, 16, 11),
        ),
    )


def small_button(text, on_click, color=GREEN, text_color=GREEN_DARK):
    """A compact outlined button used for per-item actions in the pantry list."""
    return ft.OutlinedButton(
        content=ft.Text(text, weight=ft.FontWeight.BOLD, color=text_color, size=12.5),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=CARD,
            side=ft.BorderSide(1.5, color),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding(10, 5, 10, 5),
        ),
    )


def progress_bar(fraction, color, width):
    """A thin shelf-life bar built from two fixed-size boxes (no flex, so it
    always lays out). 'fraction' (0..1) = how much shelf life has been used."""
    fraction = max(0.03, min(1.0, fraction))   # always show a sliver
    return ft.Container(
        width=width, height=8, bgcolor=TRACK, border_radius=4,
        content=ft.Container(width=width * fraction, height=8,
                             bgcolor=color, border_radius=4),
    )


# ---------------------------------------------------------------------------
# The persistent top app bar (matches the other SharedPantry screens)
# ---------------------------------------------------------------------------
def build_app_bar(active_tab, on_achievements=None):
    def tab(name):
        on = name == active_tab
        return ft.Container(
            content=ft.Text(
                name,
                size=15,
                weight=ft.FontWeight.BOLD,
                color=GREEN_DARK if on else SECONDARY,
            ),
            bgcolor=GREEN_TINT if on else None,
            border_radius=999,
            padding=ft.Padding(16, 8, 16, 8),
        )

    logo = ft.Row(
        spacing=10,
        controls=[
            ft.Container(
                content=ft.Text("SP", size=18, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                width=36, height=36, bgcolor=GREEN, border_radius=10,
                alignment=ft.alignment.center,
            ),
            ft.Text("SharedPantry", size=20, weight=ft.FontWeight.BOLD, color=GREEN_DARK),
        ],
    )

    tabs = ft.Row(
        spacing=4, wrap=True,
        controls=[tab(t) for t in
                  ["Home", "Food IQ Scanner", "My Pantry", "Share",
                   "Donate", "My Circle", "Impact"]],
    )

    achievements = ft.Container(
        content=ft.Text("🏆 Achievements", size=14, weight=ft.FontWeight.BOLD,
                        color=GREEN_DARK),
        border=ft.border.all(1.5, GREEN), border_radius=RADIUS_INPUT,
        padding=ft.Padding(14, 8, 14, 8),
        on_click=(lambda e: on_achievements()) if on_achievements else None,
    )

    avatar = ft.Container(
        content=ft.Text("Y", weight=ft.FontWeight.BOLD, color=GREEN),
        width=38, height=38, bgcolor=GREEN_TINT, border_radius=999,
        alignment=ft.alignment.center,
        on_click=(lambda e: on_achievements()) if on_achievements else None,
    )

    return ft.Container(
        bgcolor=CARD,
        border=ft.border.only(bottom=ft.BorderSide(1, CARD_BORDER)),
        padding=ft.Padding(28, 14, 28, 14),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[logo, tabs, ft.Container(expand=True), achievements, avatar],
            spacing=18,
        ),
    )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "SharedPantry — Add to Pantry"
    page.bgcolor = BG
    page.fonts = {"Nunito": "https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito%5Bwght%5D.ttf"}
    page.theme = ft.Theme(font_family="Nunito")
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    init_db()

    def toast(message):
        """Show a short pop-up message at the bottom of the window."""
        page.overlay.append(
            ft.SnackBar(content=ft.Text(message, color="#FFFFFF"),
                        bgcolor=GREEN_DARK, open=True)
        )
        page.update()

    # Which pantry filter is selected right now (drives the chip row + the list).
    ui = {"filter": "Expiring first"}

    # ---- state for the Add-to-Pantry form -------------------------------
    # We store the best-by as an ABSOLUTE calendar date. That way it stays
    # fixed (e.g. Nov 12, 2026) as the days pass — only the "days left"
    # countdown changes each day, which is what a real best-by date does.
    MAX_DAYS = 365                       # slider goes Today .. 1 yr

    state = {
        "name": "",                                            # typed by the user
        "best_by": date.today() + timedelta(days=DEFAULT_BEST_BY_DAYS),
        "qty": 1,
        "unit": "items",
        "location": "Shelf",
        "note": "",
        "safety_class": "sealed_packaged",                     # from the Food type picker
        "saving": False,                                       # guards against a double-save
    }

    def best_by_date():
        return state["best_by"]

    def days_from_today():
        """How many days from today until the best-by date (clamped to slider)."""
        d = (state["best_by"] - date.today()).days
        return max(0, min(MAX_DAYS, d))

    # ----- Best-by controls ----------------------------------------------
    best_by_chip = chip("", GREEN_TINT, GREEN_DARK)

    def set_best_by_text():
        """Update the chip's text only. Safe to call before it's on the page."""
        d = best_by_date()
        pretty = d.strftime("%b %d, %Y")
        days = (d - date.today()).days
        if days < 0:
            when = "expired"
        elif days == 0:
            when = "expires today"
        elif days == 1:
            when = "1 day left"
        else:
            when = f"{days} days left"
        best_by_chip.content.value = f"{pretty}  ·  {when}  —  drag to adjust"

    def on_slider_change(e):
        # Dragging picks a number of days from TODAY, which we turn back into
        # an absolute date and remember.
        state["best_by"] = date.today() + timedelta(days=int(e.control.value))
        set_best_by_text()
        best_by_chip.update()   # chip is on the page now, so this is safe

    slider = ft.Slider(
        min=0, max=MAX_DAYS, value=days_from_today(), divisions=MAX_DAYS,
        active_color=GREEN, inactive_color=TRACK, thumb_color=GREEN,
        on_change=on_slider_change, expand=True,
    )

    best_by_section = ft.Column(
        spacing=6,
        controls=[
            field_label("Best-by date"),
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Today", size=13.5, color=SECONDARY),
                    slider,
                    ft.Text("1 yr", size=13.5, color=SECONDARY),
                ],
            ),
            best_by_chip,
        ],
    )

    # ----- Item name -----------------------------------------------------
    def on_name_change(e):
        state["name"] = e.control.value
        if e.control.value.strip() and name_field.error_text:
            name_field.error_text = None
            name_field.update()

    name_field = ft.TextField(
        value=state["name"], hint_text="e.g. Canned tomato soup",
        on_change=on_name_change,
        border_color=INPUT_BORDER, focused_border_color=GREEN,
        border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
        content_padding=ft.Padding(14, 11, 14, 11),
    )
    name_section = ft.Column(spacing=4, controls=[field_label("Item name"), name_field])

    # ----- Food type (sets the safety class) -----------------------------
    def on_food_type_change(e):
        state["safety_class"] = e.control.value

    food_type_dd = ft.Dropdown(
        value=state["safety_class"],
        options=[ft.dropdown.Option(key=k, text=t) for k, t in FOOD_TYPES],
        on_change=on_food_type_change,
        border_color=INPUT_BORDER, border_radius=RADIUS_INPUT,
        bgcolor=CARD, text_size=14, expand=True,
    )
    food_type_section = ft.Column(
        spacing=4, expand=True,
        controls=[field_label("Food type"), food_type_dd],
    )

    # ----- Quantity + unit -----------------------------------------------
    def on_qty_change(e):
        txt = e.control.value.strip()
        state["qty"] = int(txt) if txt.isdigit() else 0

    qty_field = ft.TextField(
        value=str(state["qty"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=on_qty_change,
        border_color=INPUT_BORDER, focused_border_color=GREEN,
        border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
        content_padding=ft.Padding(12, 10, 12, 10), width=90,
    )

    def on_unit_change(e):
        state["unit"] = e.control.value

    unit_dd = ft.Dropdown(
        value=state["unit"],
        options=[ft.dropdown.Option(key=u, text=u) for u in
                 ["cans", "boxes", "bags", "jars", "bottles", "items", "lb"]],
        on_change=on_unit_change,
        border_color=INPUT_BORDER, border_radius=RADIUS_INPUT,
        bgcolor=CARD, text_size=14, expand=True,
    )

    quantity_section = ft.Column(
        spacing=4, expand=True,
        controls=[
            field_label("Quantity"),
            ft.Row(spacing=8, controls=[qty_field, unit_dd]),
        ],
    )

    # ----- Location -------------------------------------------------------
    def on_location_change(e):
        state["location"] = e.control.value

    location_dd = ft.Dropdown(
        value=state["location"],
        options=[ft.dropdown.Option(key=l, text=l) for l in
                 ["Shelf", "Fridge", "Freezer", "Pantry", "Counter"]],
        on_change=on_location_change,
        border_color=INPUT_BORDER, border_radius=RADIUS_INPUT,
        bgcolor=CARD, text_size=14, expand=True,
    )

    location_section = ft.Column(
        spacing=4, expand=True,
        controls=[field_label("Location"), location_dd],
    )

    # ----- Note for the family -------------------------------------------
    def on_note_change(e):
        state["note"] = e.control.value

    note_field = ft.TextField(
        hint_text='e.g. "Good for soup night Thursday"',
        on_change=on_note_change,
        border_color=INPUT_BORDER, focused_border_color=GREEN,
        border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
        content_padding=ft.Padding(14, 11, 14, 11),
    )

    note_section = ft.Column(
        spacing=4,
        controls=[field_label("Note for the family"), note_field],
    )

    # ----- Save / Cancel --------------------------------------------------
    def go_pantry(e=None):
        render_pantry_list()

    def save_and_go(e):
        # Guard against a double-save (e.g. an accidental double-click or a
        # replayed tap). Only the first press actually saves.
        if state.get("saving"):
            return
        if not state["name"].strip():
            name_field.error_text = "Enter an item name"
            name_field.update()
            return
        if state["qty"] <= 0:
            qty_field.error_text = "Enter a number"
            qty_field.update()
            return
        state["saving"] = True
        save_item(
            name=state["name"].strip(),
            best_by=best_by_date(),
            qty=int(state["qty"]),
            unit=state["unit"],
            location=state["location"],
            notes=state["note"],
            safety_class=state["safety_class"],
        )
        page.overlay.append(
            ft.SnackBar(
                content=ft.Text(f"Saved to your Shared Pantry ({state['location']}) ✓",
                                color="#FFFFFF"),
                bgcolor=GREEN, open=True,
            )
        )
        render_pantry_list()

    actions = ft.Row(
        alignment=ft.MainAxisAlignment.END, spacing=12,
        controls=[
            secondary_button("Cancel", go_pantry),
            primary_button("Save to Pantry", save_and_go),
        ],
    )

    # ----- Assemble the Add-to-Pantry screen -----------------------------
    def add_to_pantry_body(scanned):
        # Push the current state values into the on-screen fields (blank for a
        # manual add, or pre-filled from a scanned item).
        name_field.value = state["name"]
        name_field.error_text = None
        food_type_dd.value = state["safety_class"]
        qty_field.value = str(state["qty"])
        qty_field.error_text = None
        unit_dd.value = state["unit"]
        location_dd.value = state["location"]
        note_field.value = state["note"]
        slider.value = days_from_today()
        state["saving"] = False   # a fresh Add screen can save again
        set_best_by_text()  # make sure chip text is current (no .update() yet)
        subtitle = ("Review the scanned item, then add it to your pantry."
                    if scanned else "Enter the item's details to add it to your pantry.")
        header = ft.Column(
            spacing=4,
            controls=[
                ft.Text("Add to Shared Pantry", size=24, weight=ft.FontWeight.BOLD, color=BODY),
                ft.Text(subtitle, size=13.5, color=SECONDARY),
            ],
        )
        form = card(
            ft.Column(
                spacing=16,
                controls=[
                    name_section,
                    ft.Row(spacing=12, controls=[food_type_section, location_section]),
                    best_by_section,
                    quantity_section,
                    note_section,
                ],
            )
        )
        back_text = "← Back to scan result" if scanned else "← Back to Shared Pantry"
        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=640, spacing=14,
                controls=[
                    ft.Container(on_click=lambda e: go_pantry(),
                                 content=ft.Text(back_text, color=GREEN, size=14)),
                    header, form, actions,
                ],
            ),
            alignment=ft.alignment.top_center,
        )

    # ----- Screen 06: the Shared Pantry list -----------------------------
    def urgency(days):
        """Pick the label + colors for how soon an item expires."""
        if days <= 2:
            return (f"{max(days, 0)} days left", "#FBE9E5", "#B5402C")   # red
        if days <= 7:
            return (f"{days} days left", "#F7E9C8", "#8F6410")           # amber
        if days < 60:
            return (f"{days} days", GREEN_TINT, GREEN_DARK)              # green
        return (f"{days // 30} months", GREEN_TINT, GREEN_DARK)          # green

    def added_ago(added_iso):
        d = (date.today() - date.fromisoformat(added_iso)).days
        if d <= 0:
            return "added today"
        if d == 1:
            return "added 1 day ago"
        return f"added {d} days ago"

    def item_actions_list(it):
        """Return the LIST of small action buttons allowed for this item.
        Every item has an 'Options' button (opens screen 07). Donate is only
        offered for sealed, in-date items — the core food-safety rule."""
        safety = it["safety_class"] or "sealed_packaged"
        item_id = it["id"]
        # 'Options' opens the per-item screen 07 for THIS item.
        buttons = [small_button("Options", lambda e, i=item_id: render_item_options(i))]
        if safety == "homemade_or_opened":
            buttons.append(small_button("Use in recipe",
                           lambda e: render_placeholder("Recipe", "Kylee's screen (M9)")))
            buttons.append(small_button("Share (Circle)",
                           lambda e: render_placeholder("Share food", "Your screen (M11)")))
        elif safety == "fresh_produce":
            buttons.append(small_button("Use in recipe",
                           lambda e: render_placeholder("Recipe", "Kylee's screen (M9)")))
            buttons.append(small_button("Share",
                           lambda e: render_placeholder("Share food", "Your screen (M11)")))
        else:  # sealed_packaged -> can be donated
            buttons.append(small_button("Donate",
                           lambda e: render_placeholder("Donate to a food bank", "Your screen (M12)"),
                           color="#2B5FA3", text_color="#2B5FA3"))
            buttons.append(small_button("Share",
                           lambda e: render_placeholder("Share food", "Your screen (M11)")))
        return buttons

    def item_card(it):
        best_by = date.fromisoformat(it["best_by"])
        days = (best_by - date.today()).days
        label, tint, strong = urgency(days)

        # How much of the shelf life has been used (for the progress bar).
        total = max(1, (best_by - date.fromisoformat(it["added_on"])).days)
        used = (date.today() - date.fromisoformat(it["added_on"])).days
        fraction_used = used / total

        CARD_W, PAD = 300, 14
        inner_w = CARD_W - PAD * 2            # width available inside the card
        return ft.Container(
            width=CARD_W,
            bgcolor=CARD, border_radius=RADIUS_CARD, padding=PAD,
            border=ft.border.all(1.5 if days <= 7 else 1,
                                 strong if days <= 7 else CARD_BORDER),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        width=inner_w,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Text(f'{it["name"]}'
                                    + (f' ×{it["qty"]}' if it["qty"] and it["qty"] > 1 else ''),
                                    weight=ft.FontWeight.BOLD, color=BODY, size=15, expand=True),
                            chip(label, tint, strong),
                        ],
                    ),
                    progress_bar(fraction_used, strong, inner_w),
                    ft.Text(
                        f'{it["location"]} · {added_ago(it["added_on"])} · '
                        f'{SAFETY[it["safety_class"] or "sealed_packaged"]["label"].lower()}',
                        size=13, color=SECONDARY, width=inner_w,
                    ),
                    ft.Row(width=inner_w, wrap=True, spacing=8, controls=item_actions_list(it)),
                ],
            ),
        )

    def render_pantry_list():
        current["render"] = render_pantry_list
        all_items = get_items()

        # Apply the selected filter.
        f = ui["filter"]
        if f in ("Fridge", "Freezer", "Shelf"):
            items = [it for it in all_items if it["location"] == f]
        else:
            items = list(all_items)          # "Expiring first" and "All"
        # get_items() already returns soonest-to-expire first, which is what
        # both "Expiring first" and the default view want.

        # Header row. (Normal Row — no wrap — so the expand spacer is valid.)
        header = ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Shared Pantry", size=24, weight=ft.FontWeight.BOLD, color=BODY),
                chip(f"{len(all_items)} item" + ("" if len(all_items) == 1 else "s")),
                ft.Container(expand=True),
                secondary_button("Add manually", lambda e: render_add_page()),
                primary_button("Scan to add",
                               lambda e: render_placeholder(
                                   "Food IQ Scanner",
                                   "Kylee's screen (M3) — scanning will pre-fill the Add form.",
                                   action=("Add manually instead", lambda e2: render_add_page()))),
            ],
        )

        # Clickable filter chips.
        def filter_chip(name):
            active = (name == ui["filter"])
            def choose(e):
                ui["filter"] = name
                render_pantry_list()
            return ft.Container(
                content=ft.Text(name, size=12.5, weight=ft.FontWeight.BOLD,
                                color="#FFFFFF" if active else SECONDARY),
                bgcolor=GREEN_DARK if active else "#F1EFE7",
                border_radius=999, padding=ft.Padding(14, 6, 14, 6),
                on_click=choose,
            )

        filters = ft.Row(
            spacing=8, wrap=True,
            controls=[filter_chip(n) for n in
                      ["Expiring first", "All", "Fridge", "Freezer", "Shelf"]],
        )

        # The grid of item cards, plus a "scan to add" tile at the end.
        scan_tile = ft.Container(
            width=300, height=150, border_radius=RADIUS_CARD,
            border=ft.border.all(1.5, "#C6C2B2"),
            alignment=ft.alignment.center,
            on_click=lambda e: render_add_page(),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER, spacing=4,
                controls=[
                    ft.Text("+ Add an item", color=GREEN_DARK, size=15,
                            weight=ft.FontWeight.BOLD),
                    ft.Text("scan or enter manually", color=SECONDARY, size=12.5),
                ],
            ),
        )
        tiles = [item_card(it) for it in items] + [scan_tile]
        # Lay the fixed-width cards out 3 per row (a plain Column of Rows —
        # the most reliable way to get a grid in Flet).
        grid = ft.Column(
            spacing=14,
            controls=[
                ft.Row(tiles[i:i + 3], spacing=14,
                       vertical_alignment=ft.CrossAxisAlignment.START)
                for i in range(0, len(tiles), 3)
            ],
        )

        # Bottom rule banner (amber).
        rule = ft.Container(
            bgcolor="#F7E9C8", border=ft.border.all(1, "#E6D5A8"),
            border_radius=RADIUS_CARD, padding=ft.Padding(16, 12, 16, 12),
            content=ft.Text(
                "💡 Pantry rule: items nearing expiry get nudged to “use, share, "
                "or donate” — opened/homemade items can only go to your Circle; "
                "sealed in-date items can go anywhere.",
                size=13.5, color="#8F6410",
            ),
        )

        body = ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                spacing=14,
                controls=[header, filters, grid, rule],
            ),
        )
        page.controls.clear()
        page.add(build_app_bar("My Pantry", render_achievements), body)
        page.update()

    # ----- Screen 07: options for one pantry item ------------------------
    def photo_placeholder(w, h):
        """A gray striped-style box that stands in for a real photo."""
        return ft.Container(
            width=w, height=h, bgcolor="#EFEDE5", border_radius=RADIUS_INPUT,
            border=ft.border.all(1.5, "#BDB9A9"), alignment=ft.alignment.center,
            content=ft.Text("item photo", size=12, color="#8A8776"),
        )

    def open_note_editor(item_id, current_note):
        """Pop up a little dialog to add or change the family note."""
        box = ft.TextField(
            value=current_note or "",
            hint_text='e.g. "Use in smoothies this week"',
            multiline=True, min_lines=2, max_lines=4,
            border_color=INPUT_BORDER, focused_border_color=GREEN,
            border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
        )

        def save(e):
            update_note(item_id, box.value.strip())
            page.pop_dialog()
            toast("Note saved.")
            render_item_options(item_id)      # redraw with the new note

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Note for the family", weight=ft.FontWeight.BOLD, color=BODY),
            content=ft.Container(width=380, content=box),
            actions=[
                ft.TextButton(content=ft.Text("Cancel", color=SECONDARY),
                              on_click=lambda e: page.pop_dialog()),
                primary_button("Save note", save),
            ],
        )
        page.show_dialog(dialog)

    def render_item_options(item_id):
        current["render"] = lambda: render_item_options(item_id)
        it = get_item(item_id)
        if it is None:                        # item was discarded / not found
            render_pantry_list()
            return

        safety = it["safety_class"] or "sealed_packaged"
        best_by = date.fromisoformat(it["best_by"])
        days = (best_by - date.today()).days
        label, tint, strong = urgency(days)
        status_word = "opened" if safety == "homemade_or_opened" else \
                      ("produce" if safety == "fresh_produce" else "sealed")

        # Top card: photo + name + meta + family note.
        note_banner = (
            ft.Container(
                bgcolor="#F7E9C8", border=ft.border.all(1, "#E6D5A8"),
                border_radius=RADIUS_INPUT, padding=ft.Padding(12, 8, 12, 8),
                content=ft.Text(f'💬 Note: "{it["notes"]}"', size=13.5, color="#8F6410"),
            ) if it["notes"] else ft.Container()
        )
        info_card = card(
            ft.Row(
                spacing=16, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    photo_placeholder(120, 100),
                    ft.Column(
                        expand=True, spacing=6,
                        controls=[
                            ft.Row(controls=[
                                ft.Text(it["name"], size=18, weight=ft.FontWeight.BOLD,
                                        color=BODY, expand=True),
                                chip(label, tint, strong),
                            ]),
                            ft.Text(
                                f'{it["location"]} · {added_ago(it["added_on"])} · {status_word}',
                                size=13.5, color=SECONDARY,
                            ),
                            note_banner,
                        ],
                    ),
                ],
            )
        )

        # Action buttons.
        use_btn = ft.FilledButton(
            content=ft.Text("🍳  Use it — see recipes", weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            on_click=lambda e: render_placeholder("Recipe", "Kylee's screen (M9)"),
            style=ft.ButtonStyle(bgcolor=GREEN,
                                 shape=ft.RoundedRectangleBorder(radius=RADIUS_INPUT),
                                 padding=ft.Padding(18, 14, 18, 14)),
        )

        def wide_outlined(text, on_click, border=GREEN, text_color=GREEN_DARK, disabled=False):
            return ft.OutlinedButton(
                content=ft.Text(text, weight=ft.FontWeight.BOLD, color=text_color),
                on_click=on_click, disabled=disabled,
                style=ft.ButtonStyle(bgcolor=CARD, side=ft.BorderSide(1.5, border),
                                     shape=ft.RoundedRectangleBorder(radius=RADIUS_INPUT),
                                     padding=ft.Padding(16, 13, 16, 13)),
            )

        # Share button text depends on the safety class.
        if safety == "homemade_or_opened":
            share_btn = wide_outlined("🤝  Share with my Circle  (opened → Circle only)",
                                      lambda e: render_placeholder("Share food", "Your screen (M11)"))
        elif safety == "fresh_produce":
            share_btn = wide_outlined("🤝  Share  (produce → Circle + Community)",
                                      lambda e: render_placeholder("Share food", "Your screen (M11)"))
        else:
            share_btn = wide_outlined("🤝  Share  (sealed → anywhere)",
                                      lambda e: render_placeholder("Share food", "Your screen (M11)"))

        # Donate is enabled only for sealed, in-date items.
        if SAFETY[safety]["can_donate"]:
            donate_btn = wide_outlined("🏦  Donate to a food bank",
                                       lambda e: render_placeholder("Donate to a food bank", "Your screen (M12)"),
                                       border="#2B5FA3", text_color="#2B5FA3")
        else:
            donate_btn = wide_outlined(f"🏦  Donate — not eligible ({status_word})",
                                       None, border="#C6C2B2", text_color="#8A8776",
                                       disabled=True)

        def do_discard(e):
            discard_item(item_id)
            toast(f"Logged waste. '{it['name']}' removed from the pantry. 🌱")
            render_pantry_list()

        discard_btn = wide_outlined("🌱  Compost / discard — logs waste", do_discard,
                                    border="#8F6410", text_color="#8F6410")
        note_btn = wide_outlined("📝  Add / edit a note",
                                 lambda e: open_note_editor(item_id, it["notes"]))

        actions_card = card(
            ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,  # buttons fill width
                controls=[
                    ft.Text("What do you want to do with it?", size=14.5,
                            weight=ft.FontWeight.BOLD, color=BODY),
                    use_btn, share_btn, donate_btn, discard_btn, note_btn,
                ],
            )
        )

        body = ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=720, spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,  # cards fill the 720 width
                controls=[
                    ft.Container(on_click=lambda e: render_pantry_list(),
                                 content=ft.Text("← Shared Pantry", color=GREEN, size=14)),
                    info_card, actions_card,
                ],
            ),
            alignment=ft.alignment.top_center,
        )
        page.controls.clear()
        page.add(build_app_bar("My Pantry", render_achievements), body)
        page.update()

    # ----- Placeholder for screens not built yet (or Kylee's) ------------
    def render_placeholder(title, note="", action=None):
        """A near-blank page for buttons whose screen isn't finished yet.
        Keeps the app bar and a back link so you're never stranded.
        'action' is an optional (label, on_click) tuple for a button."""
        current["render"] = lambda: render_placeholder(title, note, action)
        controls = [
            ft.Text("🚧", size=40),
            ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=BODY),
            ft.Text("This screen isn't built yet.", size=14, color=SECONDARY),
        ]
        if note:
            controls.append(ft.Text(note, size=13, color=SECONDARY))
        if action:
            controls.append(ft.Container(height=6))
            controls.append(primary_button(action[0], action[1]))
        placeholder = card(
            ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      spacing=10, controls=controls),
            padding=48,
        )
        body = ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=720, spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(on_click=lambda e: render_pantry_list(),
                                 content=ft.Text("← Back to Shared Pantry", color=GREEN, size=14)),
                    placeholder,
                ],
            ),
            alignment=ft.alignment.top_center,
        )
        page.controls.clear()
        page.add(build_app_bar("My Pantry", render_achievements), body)
        page.update()

    # ----- Achievements page (real numbers from your pantry) -------------
    def render_achievements():
        current["render"] = render_achievements
        s = get_stats()

        def stat_card(number, label, color):
            return ft.Container(
                expand=True, bgcolor=CARD, border_radius=RADIUS_CARD,
                border=ft.border.all(1, CARD_BORDER), padding=18,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
                    controls=[
                        ft.Text(str(number), size=30, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(label, size=13, color=SECONDARY,
                                text_align=ft.TextAlign.CENTER),
                    ],
                ),
            )

        # Each badge: (emoji, title, how-to, earned?)  — all based on real counts.
        badges = [
            ("🥫", "First item",     "Add your first item",            s["total"] >= 1),
            ("📦", "Getting started","Add 5 items",                    s["total"] >= 5),
            ("🏠", "Well stocked",   "Keep 10 items in your pantry",   s["in_pantry"] >= 10),
            ("♻️", "Waste tracker",  "Log a composted item",           s["composted"] >= 1),
            ("🤝", "First share",    "Share an item (coming soon)",    False),
            ("🏦", "First donation", "Donate an item (coming soon)",   False),
        ]

        def badge_card(emoji, title, how, earned):
            return ft.Container(
                width=300, bgcolor=CARD if earned else "#FAF9F5",
                border_radius=RADIUS_CARD, padding=14,
                border=ft.border.all(1.5 if earned else 1,
                                     GREEN if earned else CARD_BORDER),
                content=ft.Row(
                    spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(emoji, size=26),
                        ft.Column(
                            spacing=2, expand=True,
                            controls=[
                                ft.Text(title, size=14, weight=ft.FontWeight.BOLD,
                                        color=BODY if earned else SECONDARY),
                                ft.Text(("Earned ✓" if earned else how),
                                        size=12.5,
                                        color=GREEN_DARK if earned else SECONDARY),
                            ],
                        ),
                    ],
                ),
            )

        cards = [badge_card(*b) for b in badges]
        badge_grid = ft.Column(
            spacing=14,
            controls=[ft.Row(cards[i:i + 3], spacing=14,
                             vertical_alignment=ft.CrossAxisAlignment.START)
                      for i in range(0, len(cards), 3)],
        )

        earned_count = sum(1 for b in badges if b[3])
        body = ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Container(on_click=lambda e: render_pantry_list(),
                                 content=ft.Text("← Back to Shared Pantry", color=GREEN, size=14)),
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Achievements", size=24, weight=ft.FontWeight.BOLD, color=BODY),
                            chip(f"{earned_count} of {len(badges)} badges earned"),
                        ],
                    ),
                    ft.Row(
                        spacing=14,
                        controls=[
                            stat_card(s["total"], "items added", GREEN_DARK),
                            stat_card(s["in_pantry"], "in your pantry now", "#2B5FA3"),
                            stat_card(s["composted"], "waste logged", "#8F6410"),
                        ],
                    ),
                    ft.Text("Badges", size=17, weight=ft.FontWeight.BOLD, color=BODY),
                    badge_grid,
                ],
            ),
        )
        page.controls.clear()
        page.add(build_app_bar("", render_achievements), body)
        page.update()

    def render_add_page(scanned=None):
        """Show the Add-to-Pantry form. Pass a scanned item dict to pre-fill it;
        with no argument it's a blank form. (Kylee's scanner will call this with
        a real item — e.g. render_add_page({"name": ..., "best_by": ...,
        "safety_class": ..., "qty": ..., "unit": ...}) — so the same form is
        reused; there is no hard-coded item anywhere.)"""
        # Reset the form, then apply anything the scanner handed us.
        state["name"] = ""
        state["best_by"] = date.today() + timedelta(days=DEFAULT_BEST_BY_DAYS)
        state["qty"] = 1
        state["unit"] = "items"
        state["location"] = "Shelf"
        state["note"] = ""
        state["safety_class"] = "sealed_packaged"
        if scanned:
            state["name"] = scanned.get("name", "")
            if scanned.get("best_by"):
                state["best_by"] = scanned["best_by"]
            state["qty"] = scanned.get("qty", 1)
            state["unit"] = scanned.get("unit", "items")
            state["safety_class"] = scanned.get("safety_class", "sealed_packaged")

        current["render"] = lambda: render_add_page(scanned)
        page.controls.clear()
        page.add(build_app_bar("My Pantry", render_achievements), add_to_pantry_body(scanned))
        page.update()

    # Remember which screen is showing, so the daily auto-refresh can redraw it.
    current = {"render": render_add_page}

    # ----- Daily auto-refresh --------------------------------------------
    # A tiny background helper wakes up every minute and, when the calendar
    # day changes (e.g. just after midnight), redraws the current screen so
    # every "days left" countdown drops by one on its own — no clicking needed.
    def watch_for_new_day():
        last_day = date.today()
        while True:
            time.sleep(60)
            today = date.today()
            if today != last_day:
                last_day = today
                try:
                    current["render"]()      # redraw with fresh countdowns
                except Exception:
                    break                    # window closed — stop the helper

    threading.Thread(target=watch_for_new_day, daemon=True).start()

    # First screen shown = the Shared Pantry list (empty until you add items).
    render_pantry_list()


if __name__ == "__main__":
    ft.app(target=main)
