"""
SharedPantry — Yaashvi's app (main.py)
======================================

This is the STARTING file: the screens and the app itself. It borrows its
styling from theme.py and its database functions from db.py.

NAVIGATION (new!)
-----------------
A tiny "App controller" (the App class below) remembers which screen is showing
and can switch to another one. Each screen is a function that just BUILDS its
look and returns it — the App is the only thing that actually draws the page
(menu bar on top, screen body below). Buttons switch screens by calling
app.navigate("some_route").

How to run it:
  * Press Run / F5 in VS Code, OR
  * In the terminal:   python main.py
"""

import threading
import time
from datetime import date, timedelta

import flet as ft

# Bring in the styling (colors + helper widgets) from theme.py, the database
# functions from db.py, and the tiny login-memory helpers from session.py.
# All three files live in this same folder, so Python imports them by file
# name (without the ".py").
from theme import (
    BG, CARD, CARD_BORDER, GREEN, GREEN_DARK, GREEN_TINT, BODY, SECONDARY,
    INPUT_BORDER, TRACK, RADIUS_CARD, RADIUS_INPUT,
    card, chip, field_label, primary_button, secondary_button, small_button,
    progress_bar,
)
from db import (
    init_db, save_item, get_items, get_item, update_note, discard_item,
    create_account, check_login, get_user, allowed_share_scopes,
    create_share, can_donate, donate_ineligible_reason, get_donatable_items,
    create_donation,
)
import session
import queries

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


# ===========================================================================
# The App controller (a.k.a. a "router")
# ===========================================================================
class App:
    """A tiny controller that remembers which screen is showing and can switch
    to another one.

    The screens don't draw the page themselves anymore. Each screen is a
    function that just BUILDS its body (the stuff below the menu bar) and hands
    it back. The App is the ONLY place that clears the page and draws:
    the menu bar on top, and the current screen's body underneath.

    Two pieces of memory:
      route -> a short name for the screen showing now, e.g. "my_pantry".
      arg   -> any extra info that screen needs, e.g. which item id to open.
    """

    def __init__(self, page, screen_for, menu_bar_for):
        self.page = page
        self.screen_for = screen_for       # function: (route, arg) -> body control
        self.menu_bar_for = menu_bar_for   # function: (route)      -> the menu bar
        self.route = "welcome"             # which screen is showing right now
        self.arg = None                    # extra info for that screen
        self.user_id = None                # who is logged in (None = nobody yet)

    def navigate(self, route, arg=None):
        """Switch to a different screen, then redraw."""
        self.route = route
        self.arg = arg
        self.render()

    def render(self):
        """Draw the current screen. The Welcome (login) screen fills the whole
        window with no menu bar; every other screen gets the menu bar on top."""
        body = self.screen_for(self.route, self.arg)
        self.page.controls.clear()
        if self.route == "welcome":
            self.page.add(body)                        # login screen: no menu bar
        else:
            self.page.add(self.menu_bar_for(self.route), body)
        self.page.update()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "SharedPantry"
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

    # Remembers the Donate flow's picks (which item, which food bank, and the
    # drop-off pass once confirmed) so they survive re-draws of the screen.
    donate_sel = {}

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
        app.navigate("my_pantry")

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
            owner_id=app.user_id,          # the item belongs to the logged-in user
        )
        toast(f"Added “{state['name'].strip()}” to your {state['location']}. ✓")
        app.navigate("my_pantry")

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
        buttons = [small_button("Options", lambda e, i=item_id: app.navigate("item_options", i))]
        if safety == "homemade_or_opened":
            buttons.append(small_button("Use in recipe",
                           lambda e: app.navigate("kylee", "Recipe")))
            buttons.append(small_button("Share (Circle)",
                           lambda e: app.navigate("share", item_id)))
        elif safety == "fresh_produce":
            buttons.append(small_button("Use in recipe",
                           lambda e: app.navigate("kylee", "Recipe")))
            buttons.append(small_button("Share",
                           lambda e: app.navigate("share", item_id)))
        else:  # sealed_packaged -> can be donated
            buttons.append(small_button("Donate",
                           lambda e: app.navigate("donate", item_id),
                           color="#2B5FA3", text_color="#2B5FA3"))
            buttons.append(small_button("Share",
                           lambda e: app.navigate("share", item_id)))
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

    def pantry_body():
        all_items = get_items(app.user_id)

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
                secondary_button("Add manually", lambda e: app.navigate("add")),
                primary_button("Scan to add",
                               lambda e: app.navigate("kylee", "Food IQ Scanner")),
            ],
        )

        # Clickable filter chips.
        def filter_chip(name):
            active = (name == ui["filter"])
            def choose(e):
                ui["filter"] = name
                app.render()          # redraw THIS same screen with the new filter
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
            on_click=lambda e: app.navigate("add"),
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
        # Bottom rule banner (amber) — the food-safety idea in one line.
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

        # Three cases: totally empty pantry, a filter that matched nothing, or
        # the normal grid of cards. Each gets a friendly message of its own.
        if not all_items:
            empty = ft.Container(
                bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
                border_radius=RADIUS_CARD, padding=40,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    controls=[
                        ft.Text("🧺", size=40),
                        ft.Text("Your pantry is empty", size=18,
                                weight=ft.FontWeight.BOLD, color=BODY),
                        ft.Text("Add your first item to start tracking freshness "
                                "and sharing food.", size=13.5, color=SECONDARY,
                                text_align=ft.TextAlign.CENTER),
                        primary_button("Add an item", lambda e: app.navigate("add")),
                    ],
                ),
            )
            middle = [empty]
        else:
            tiles = [item_card(it) for it in items] + [scan_tile]
            grid = ft.Column(
                spacing=14,
                controls=[
                    ft.Row(tiles[i:i + 3], spacing=14,
                           vertical_alignment=ft.CrossAxisAlignment.START)
                    for i in range(0, len(tiles), 3)
                ],
            )
            middle = [filters]
            if not items:            # you have items, but none match this filter
                middle.append(ft.Text(f"No items in {ui['filter']} — try another filter.",
                                      size=14, color=SECONDARY))
            middle.append(grid)
            middle.append(rule)

        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(spacing=14, controls=[header] + middle),
        )

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
            page.close(dialog)                # close the popup (Flet 0.24.1 way)
            toast("Note saved.")
            app.navigate("item_options", item_id)   # redraw with the new note

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Note for the family", weight=ft.FontWeight.BOLD, color=BODY),
            content=ft.Container(width=380, content=box),
            actions=[
                ft.TextButton(content=ft.Text("Cancel", color=SECONDARY),
                              on_click=lambda e: page.close(dialog)),
                primary_button("Save note", save),
            ],
        )
        page.open(dialog)

    def item_options_body(item_id):
        it = get_item(item_id)
        if it is None:                        # item was discarded / not found
            return pantry_body()

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
            on_click=lambda e: app.navigate("kylee", "Recipe"),
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
                                      lambda e: app.navigate("share", item_id))
        elif safety == "fresh_produce":
            share_btn = wide_outlined("🤝  Share  (produce → Circle + Community)",
                                      lambda e: app.navigate("share", item_id))
        else:
            share_btn = wide_outlined("🤝  Share  (sealed → anywhere)",
                                      lambda e: app.navigate("share", item_id))

        # Donate is enabled only for sealed, in-date items. For everything else
        # we still let the button open the Donate flow — it shows a friendly
        # banner explaining WHY the item can't be donated.
        if SAFETY[safety]["can_donate"]:
            donate_btn = wide_outlined("🏦  Donate to a food bank",
                                       lambda e: app.navigate("donate", item_id),
                                       border="#2B5FA3", text_color="#2B5FA3")
        else:
            donate_btn = wide_outlined(f"🏦  Why can't I donate this? ({status_word})",
                                       lambda e: app.navigate("donate", item_id),
                                       border="#C6C2B2", text_color="#8A8776")

        def do_discard(e):
            discard_item(item_id)
            toast(f"Logged waste. '{it['name']}' removed from the pantry. 🌱")
            app.navigate("my_pantry")

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

        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=720, spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,  # cards fill the 720 width
                controls=[
                    ft.Container(on_click=lambda e: app.navigate("my_pantry"),
                                 content=ft.Text("← Back to Shared Pantry", color=GREEN, size=14)),
                    info_card, actions_card,
                ],
            ),
            alignment=ft.alignment.top_center,
        )

    # ----- Share form (Piece 1 of the Share flow) ------------------------
    def audience_text(safety):
        """Turn the db.py food-safety rule into friendly words for the screen."""
        scopes = allowed_share_scopes(safety)
        names = {"circle": "My Circle", "community": "Community", "food_bank": "Food banks"}
        if scopes == ["circle"]:
            return "visible only to My Circle"
        return " + ".join(names[s] for s in scopes)

    SHARE_TYPES = [
        ("homemade_or_opened", "Homemade / opened"),
        ("sealed_packaged",    "Sealed & packaged"),
        ("fresh_produce",      "Fresh produce (uncut)"),
    ]
    TYPE_LABEL = {k: lbl for k, lbl in SHARE_TYPES}

    def share_body(item_id=None):
        """The Share form. If item_id is given, the share is LOCKED to that
        pantry item's food type (so you can never broaden the audience)."""
        locked_item = get_item(item_id) if item_id else None

        if locked_item:
            default_safety = locked_item["safety_class"] or "homemade_or_opened"
            qty = locked_item["qty"]
            prefill = locked_item["name"] + (f" ×{qty}" if qty and qty > 1 else "")
        else:
            default_safety = "homemade_or_opened"
            prefill = ""

        title_in = ft.TextField(
            value=prefill,
            hint_text="Name & quantity — e.g. Veggie pasta bake, serves 4",
            border_color=INPUT_BORDER, focused_border_color=GREEN,
            border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
            content_padding=ft.Padding(14, 12, 14, 12),
        )
        best_by_dd = ft.Dropdown(
            hint_text="Made / best-by date",
            options=[ft.dropdown.Option(x) for x in
                     ["Made today", "Best by this week", "Best by next week", "Best by this month"]],
            border_color=INPUT_BORDER, border_radius=RADIUS_INPUT,
            bgcolor=CARD, text_size=14, expand=True,
        )
        pickup_dd = ft.Dropdown(
            hint_text="Pickup window",
            options=[ft.dropdown.Option(x) for x in
                     ["Today 5–7pm", "Tomorrow morning", "This weekend", "Anytime — message me"]],
            border_color=INPUT_BORDER, border_radius=RADIUS_INPUT,
            bgcolor=CARD, text_size=14, expand=True,
        )
        err = ft.Text("", size=13, color="#B5402C")

        # The food-type chooser. Locked items show a fixed note; free shares get radios.
        if locked_item:
            get_safety = lambda: default_safety
            type_inner = ft.Container(
                bgcolor="#FAF7EC", border=ft.border.all(1, "#E6D5A8"),
                border_radius=RADIUS_INPUT, padding=ft.Padding(14, 10, 14, 10),
                content=ft.Text(
                    f"Locked to this item: {TYPE_LABEL[default_safety]}  →  "
                    f"{audience_text(default_safety)}.  Food-safety rules set the "
                    f"audience — you can't broaden it.",
                    size=13.5, color="#8F6410"),
            )
        else:
            radio = ft.RadioGroup(
                value=default_safety,
                content=ft.Column(spacing=6, controls=[
                    ft.Radio(value=k, label=f"{lbl}   →   {audience_text(k)}")
                    for k, lbl in SHARE_TYPES
                ]),
            )
            get_safety = lambda: radio.value
            type_inner = radio

        type_card = card(
            ft.Column(spacing=10, controls=[
                ft.Text("What kind of food is it?", size=15,
                        weight=ft.FontWeight.BOLD, color=BODY),
                type_inner,
            ])
        )

        form_card = card(
            ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                photo_placeholder(120, 90),
                ft.Column(expand=True, spacing=10, controls=[
                    title_in,
                    ft.Row(spacing=10, controls=[best_by_dd, pickup_dd]),
                ]),
            ])
        )

        def submit(e):
            title = (title_in.value or "").strip()
            if not title:
                err.value = "Give it a name & quantity first."
                err.update(); return
            create_share(
                shared_by=app.user_id, item_id=item_id, title=title,
                safety_class=get_safety(),
                best_by=best_by_dd.value, pickup_window=pickup_dd.value,
            )
            toast(f"Shared “{title}” — {audience_text(get_safety())}. ✓")
            app.navigate("my_pantry")

        header = ft.Column(spacing=4, controls=[
            ft.Text("Share food", size=24, weight=ft.FontWeight.BOLD, color=BODY),
            ft.Text("What you share and who can see it depends on food-safety "
                    "rules — we handle that for you.", size=13.5, color=SECONDARY),
        ])
        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(width=760, spacing=14, controls=[
                header, type_card, form_card, err,
                ft.Row(alignment=ft.MainAxisAlignment.END,
                       controls=[primary_button("Share it", submit)]),
            ]),
            alignment=ft.alignment.top_center,
        )

    # ----- Donate flow (3 steps on one screen) ---------------------------
    def donate_body(arg=None):
        """Donate to a food bank. arg is either the pantry item you arrived from
        (int), None (from the menu tab), or the string "keep" (a re-draw after a
        selection, which must NOT reset your picks)."""
        if arg != "keep":
            reason = None
            preselect = None
            if arg:                                   # arrived from a pantry item
                it = get_item(arg)
                if it and can_donate(it["safety_class"], it["best_by"]):
                    preselect = arg
                elif it:
                    reason = donate_ineligible_reason(it["safety_class"], it["best_by"])
            donate_sel.clear()
            donate_sel.update({"item_id": preselect, "bank_id": None,
                               "reason": reason, "created_id": None})

        eligible = get_donatable_items(app.user_id)
        banks = queries.get_food_banks()
        sel_item = next((it for it in eligible if it["id"] == donate_sel.get("item_id")), None)
        sel_bank = next((b for b in banks if b["id"] == donate_sel.get("bank_id")), None)

        def pick_item(item_id):
            donate_sel["item_id"] = item_id
            donate_sel["created_id"] = None           # starting a new pass
            app.navigate("donate", "keep")

        def pick_bank(bank_id):
            donate_sel["bank_id"] = bank_id
            donate_sel["created_id"] = None
            app.navigate("donate", "keep")

        def step_header(n, title):
            return ft.Column(spacing=8, controls=[
                ft.Container(
                    content=ft.Text(f"STEP {n}", size=12, weight=ft.FontWeight.BOLD,
                                    color=GREEN_DARK),
                    bgcolor=GREEN_TINT, border_radius=999,
                    padding=ft.Padding(12, 4, 12, 4),
                ),
                ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=BODY),
            ])

        # ----- STEP 1: does it qualify? + pick an eligible item -----
        def check_row(text, ok):
            return ft.Row(spacing=8, controls=[
                ft.Text("✅" if ok else "☐", size=14),
                ft.Text(text, size=13.5, color=BODY if ok else SECONDARY),
            ])
        checklist = ft.Column(spacing=4, controls=[
            check_row("Sealed / unopened packaging", True),
            check_row('Before "best by" date', True),
            check_row("Ingredient label intact", True),
            check_row("Not homemade or reheated", False),
            check_row("No damaged / bulging cans", False),
        ])
        step1_controls = [step_header(1, "Does it qualify?"), checklist]
        if donate_sel.get("reason"):
            step1_controls.append(ft.Container(
                bgcolor="#FAF7EC", border=ft.border.all(1, "#E6D5A8"),
                border_radius=RADIUS_INPUT, padding=ft.Padding(12, 8, 12, 8),
                content=ft.Text(donate_sel["reason"], size=13, color="#8F6410"),
            ))
        step1_controls.append(ft.Text("Choose an item to donate", size=13.5,
                                      weight=ft.FontWeight.BOLD, color=BODY))
        if eligible:
            for it in eligible:
                chosen = (sel_item and it["id"] == sel_item["id"])
                step1_controls.append(ft.Container(
                    on_click=lambda e, i=it["id"]: pick_item(i),
                    bgcolor=GREEN_TINT if chosen else CARD,
                    border=ft.border.all(1.5 if chosen else 1,
                                         GREEN if chosen else CARD_BORDER),
                    border_radius=RADIUS_INPUT, padding=ft.Padding(12, 10, 12, 10),
                    content=ft.Text(f'{it["name"]}' + (f' ×{it["qty"]}' if it["qty"] > 1 else ''),
                                    size=14, weight=ft.FontWeight.BOLD,
                                    color=GREEN_DARK if chosen else BODY),
                ))
        else:
            step1_controls.append(ft.Text("You have no sealed, in-date items to "
                                          "donate right now.", size=13, color=SECONDARY))
        step1 = ft.Container(
            width=300, bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
            border_radius=RADIUS_CARD, padding=18,
            content=ft.Column(spacing=12, controls=step1_controls),
        )

        # ----- STEP 2: pick a food bank -----
        step2_controls = [step_header(2, "Pick a food bank")]
        for b in banks:
            chosen = (sel_bank and b["id"] == sel_bank["id"])
            step2_controls.append(ft.Container(
                on_click=lambda e, i=b["id"]: pick_bank(i),
                bgcolor=CARD, border=ft.border.all(2 if chosen else 1,
                                                   "#2B5FA3" if chosen else CARD_BORDER),
                border_radius=RADIUS_CARD, padding=14,
                content=ft.Column(spacing=2, controls=[
                    ft.Text(("◉ " if chosen else "○ ") + b["name"], size=15,
                            weight=ft.FontWeight.BOLD, color=BODY),
                    ft.Text(f'{b["distance_mi"]} mi · needs: {b["accepts"]} · {b["schedule"]}',
                            size=13, color=SECONDARY),
                ]),
            ))
        step2 = ft.Container(
            width=300, bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
            border_radius=RADIUS_CARD, padding=18,
            content=ft.Column(spacing=12, controls=step2_controls),
        )

        # ----- STEP 3: drop-off pass -----
        def qr_box():
            return ft.Container(
                width=150, height=150, bgcolor="#EFEDE5", border_radius=RADIUS_INPUT,
                border=ft.border.all(1.5, "#BDB9A9"), alignment=ft.alignment.center,
                content=ft.Text("QR code", size=12, color="#8A8776"),
            )

        step3_controls = [step_header(3, "Your drop-off pass")]
        if donate_sel.get("created_id"):
            did = donate_sel["created_id"]
            step3_controls.append(ft.Container(
                bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
                border_radius=RADIUS_CARD, padding=18,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    controls=[
                        qr_box(),
                        ft.Text(f"Donation #{did:04d}", size=17,
                                weight=ft.FontWeight.BOLD, color=BODY),
                        ft.Text(f'{donate_sel["created_title"]} · {donate_sel["created_bank"]}',
                                size=13.5, color=SECONDARY, text_align=ft.TextAlign.CENTER),
                        ft.Text(f'{donate_sel["created_window"]} · show at desk',
                                size=13.5, color=SECONDARY),
                        ft.Container(
                            on_click=lambda e, i=donate_sel["created_bank_id"]:
                                app.navigate("food_bank_dashboard", i),
                            content=ft.Text(f'View {donate_sel["created_bank"]} dashboard →',
                                            color=GREEN, size=13.5, weight=ft.FontWeight.BOLD)),
                    ],
                ),
            ))
        elif sel_item and sel_bank:
            def confirm(e):
                try:
                    did = create_donation(app.user_id, sel_item["id"], sel_bank["id"],
                                          dropoff_window=sel_bank["schedule"])
                except ValueError as ex:
                    toast(str(ex)); return
                donate_sel["created_id"] = did
                donate_sel["created_title"] = (sel_item["name"] +
                                               (f' ×{sel_item["qty"]}' if sel_item["qty"] > 1 else ''))
                donate_sel["created_bank"] = sel_bank["name"]
                donate_sel["created_bank_id"] = sel_bank["id"]
                donate_sel["created_window"] = sel_bank["schedule"]
                toast(f"Drop-off pass ready — Donation #{did:04d}")
                app.navigate("donate", "keep")
            step3_controls.append(ft.Container(
                bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
                border_radius=RADIUS_CARD, padding=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text(f'{sel_item["name"]}' + (f' ×{sel_item["qty"]}' if sel_item["qty"] > 1 else ''),
                            size=15, weight=ft.FontWeight.BOLD, color=BODY),
                    ft.Text(f'{sel_bank["name"]} · {sel_bank["schedule"]}',
                            size=13.5, color=SECONDARY),
                    primary_button("Confirm drop-off slot", confirm),
                ]),
            ))
        else:
            step3_controls.append(ft.Text("Pick an item and a food bank to get your "
                                          "drop-off pass.", size=13, color=SECONDARY))
        step3 = ft.Container(
            width=300, bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
            border_radius=RADIUS_CARD, padding=18,
            content=ft.Column(spacing=12, controls=step3_controls),
        )

        header = ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Donate to a food bank", size=24, weight=ft.FontWeight.BOLD, color=BODY),
                ft.Text(f"{len(banks)} partner banks enrolled near you", size=13.5, color=SECONDARY),
                ft.Container(expand=True),
                ft.Container(
                    on_click=lambda e: app.navigate("food_bank_dashboard", banks[0]["id"]) if banks else None,
                    content=ft.Text("View a partner dashboard →", color=GREEN, size=13.5,
                                    weight=ft.FontWeight.BOLD)),
            ],
        )
        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(spacing=16, controls=[
                header,
                ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START,
                       wrap=True, controls=[step1, step2, step3]),
            ]),
        )

    # ----- Food-bank partner dashboard -----------------------------------
    def dashboard_body(bank_id):
        bank = queries.get_food_bank(bank_id)
        if bank is None:
            return donate_body()
        incoming = queries.get_incoming_donations(bank_id)

        def donation_row(d):
            checked = (d["status"] == "checked_in")
            right = (ft.Text("✓ checked in", size=13, weight=ft.FontWeight.BOLD, color=GREEN_DARK)
                     if checked else
                     small_button("Check in",
                                  lambda e, i=d["id"]: (queries.check_in_donation(i),
                                                        app.navigate("food_bank_dashboard", bank_id))))
            return ft.Container(
                bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
                border_radius=RADIUS_CARD, padding=14,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
                    controls=[
                        chip(f'#{d["id"]:04d}'),
                        ft.Column(expand=True, spacing=2, controls=[
                            ft.Text(f'{d["item_name"]}' + (f' ×{d["qty"]}' if d["qty"] > 1 else ''),
                                    size=15, weight=ft.FontWeight.BOLD, color=BODY),
                            ft.Text(f'{d["donor_name"]} · verified sealed & in-date ✓',
                                    size=13, color=SECONDARY),
                        ]),
                        right,
                    ],
                ),
            )

        rows = [donation_row(d) for d in incoming] or [
            ft.Text("No incoming donations yet.", size=13, color=SECONDARY)]
        incoming_card = card(ft.Column(spacing=12, controls=[
            ft.Text(f'Incoming donations ({bank["schedule"]})', size=15,
                    weight=ft.FontWeight.BOLD, color=BODY),
            *rows,
        ]))

        need_chips = ft.Row(wrap=True, spacing=8, controls=[
            chip(n.strip()) for n in (bank["accepts"] or "").split(",") if n.strip()])
        needs_card = card(ft.Column(spacing=10, controls=[
            ft.Text("Current needs", size=15, weight=ft.FontWeight.BOLD, color=BODY),
            need_chips,
            ft.Text("These needs show up on members' Donate screens.",
                    size=13, color=SECONDARY),
            ft.Text(f'{len(incoming)} donations logged with this partner so far.',
                    size=13.5, weight=ft.FontWeight.BOLD, color=GREEN_DARK),
        ]))

        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(width=980, spacing=14, controls=[
                ft.Container(on_click=lambda e: app.navigate("donate"),
                             content=ft.Text("← Back to Donate", color=GREEN, size=14)),
                ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Text(f'{bank["name"]} — partner dashboard', size=24,
                            weight=ft.FontWeight.BOLD, color=BODY),
                    chip("enrolled partner"),
                ]),
                ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START,
                       wrap=True, controls=[
                    ft.Container(width=480, content=incoming_card),
                    ft.Container(width=360, content=needs_card),
                ]),
            ]),
        )

    # ----- My Circle screen ----------------------------------------------
    def circle_body():
        """Your Circle: the members list, pending invites, and an invite box.
        A Circle is the small group of people you personally know and trust —
        and (see the amber note) the ONLY people who can ever receive your
        homemade/opened food, because of the food-safety rule in db.py."""
        me = get_user(app.user_id)
        circle = queries.get_or_create_circle(app.user_id, me["name"] if me else "Member")
        members = queries.get_circle_members(circle["id"])
        pending = queries.get_pending_invites(circle["id"])

        invite_input = ft.TextField(
            hint_text="Phone number or email…",
            border_color=INPUT_BORDER, focused_border_color=GREEN,
            border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
            content_padding=ft.Padding(14, 12, 14, 12),
        )
        invite_err = ft.Text("", size=13, color="#B5402C")

        def looks_like_contact(text):
            """A light check that it's a real-ish email OR phone number."""
            t = text.strip()
            if "@" in t and "." in t.split("@")[-1] and len(t) >= 5:
                return True                          # e.g. name@example.com
            digits = [ch for ch in t if ch.isdigit()]
            return len(digits) >= 7                  # a phone number has 7+ digits

        def send_invite(e):
            contact = (invite_input.value or "").strip()
            if not contact:
                invite_err.value = "Type a phone number or email first."
                invite_err.update(); return
            if not looks_like_contact(contact):
                invite_err.value = "That doesn't look like a valid email or phone number."
                invite_err.update(); return
            code = queries.create_invite(circle["id"], contact, app.user_id)
            toast(f"Invite created for {contact} — code {code}")
            app.render()          # redraw so the new pending invite shows up

        def copy_link(e):
            link = f"sharedpantry://join/{circle['id']}"
            page.set_clipboard(link)
            toast("Your Circle invite link was copied to the clipboard.")

        def avatar_circle(letter):
            return ft.Container(
                content=ft.Text(letter, weight=ft.FontWeight.BOLD, color=GREEN),
                width=44, height=44, bgcolor=GREEN_TINT, border_radius=999,
                alignment=ft.alignment.center,
            )

        # --- one member card ---
        def member_card(m):
            is_owner = (m["role"] == "owner")
            if is_owner:
                subtitle = f"owner of this Circle · shared {m['shared_count']} items"
                tag = chip("you")
            else:
                bits = []
                if m["relation"]:
                    bits.append(m["relation"])
                if m["distance_mi"] is not None:
                    bits.append(f"{m['distance_mi']} mi")
                bits.append(f"shared {m['shared_count']} items")
                subtitle = " · ".join(bits)
                tag = chip("active")
            return ft.Container(
                bgcolor=CARD, border=ft.border.all(1, CARD_BORDER),
                border_radius=RADIUS_CARD, padding=14,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                    controls=[
                        avatar_circle((m["name"][:1] or "?").upper()),
                        ft.Column(
                            expand=True, spacing=2,
                            controls=[
                                ft.Text(m["name"], size=15, weight=ft.FontWeight.BOLD, color=BODY),
                                ft.Text(subtitle, size=13, color=SECONDARY),
                            ],
                        ),
                        tag,
                    ],
                ),
            )

        # --- one pending-invite card (tinted, like the design) ---
        def pending_card(inv):
            return ft.Container(
                bgcolor="#FAF7EC", border=ft.border.all(1.5, "#E6D5A8"),
                border_radius=RADIUS_CARD, padding=14,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                    controls=[
                        avatar_circle("?"),
                        ft.Column(
                            expand=True, spacing=2,
                            controls=[
                                ft.Text(f'{inv["invited_email"]} — pending', size=15,
                                        weight=ft.FontWeight.BOLD, color=BODY),
                                ft.Text(f'invited by {inv["method"] or "link"} · '
                                        f'code {inv["code"] or "—"} · {inv["created_on"]}',
                                        size=13, color=SECONDARY),
                            ],
                        ),
                        small_button("Resend invite",
                                     lambda e, c=inv["code"]: toast(f"Invite link re-sent (code {c}).")),
                    ],
                ),
            )

        # --- LEFT column: header + members + pending ---
        member_count = len(members)
        left_controls = [
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("My Circle", size=24, weight=ft.FontWeight.BOLD, color=BODY),
                    chip(f"{member_count} member" + ("" if member_count == 1 else "s")),
                ],
            ),
        ]
        left_controls += [member_card(m) for m in members]
        if pending:
            left_controls.append(ft.Text("Pending invites", size=15,
                                         weight=ft.FontWeight.BOLD, color=BODY))
            left_controls += [pending_card(inv) for inv in pending]
        left = ft.Column(width=520, spacing=12, controls=left_controls)

        # --- RIGHT column: invite box + trust note ---
        invite_card = card(
            ft.Column(
                spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Text("Invite someone you trust", size=17,
                            weight=ft.FontWeight.BOLD, color=BODY),
                    invite_input,
                    invite_err,
                    primary_button("Send invite link", send_invite),
                    ft.Text("— or —", size=13, color=SECONDARY,
                            text_align=ft.TextAlign.CENTER),
                    secondary_button("📋  Copy my invite link", copy_link),
                ],
            )
        )

        # The trust note. Its last line comes STRAIGHT from the db.py rule, so
        # the words can never drift away from what the code actually does.
        homemade_circle_only = (allowed_share_scopes("homemade_or_opened") == ["circle"])
        rule_line = ("Only Circle members ever see homemade food."
                     if homemade_circle_only else
                     "Homemade food can be shared more widely.")
        trust_note = ft.Container(
            bgcolor="#FAF7EC", border=ft.border.all(1, "#E6D5A8"),
            border_radius=RADIUS_CARD, padding=ft.Padding(16, 12, 16, 12),
            content=ft.Column(spacing=4, controls=[
                ft.Text("Your Circle = people you personally know.", size=13.5,
                        weight=ft.FontWeight.BOLD, color="#8F6410"),
                ft.Text(f"They must accept and be nearby. {rule_line}",
                        size=13.5, color="#8F6410"),
            ]),
        )
        right = ft.Column(width=360, spacing=14, controls=[invite_card, trust_note])

        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Row(spacing=20, wrap=True,
                           vertical_alignment=ft.CrossAxisAlignment.START,
                           controls=[left, right]),
        )

    # ----- "Coming soon" page for MY screens that aren't built yet --------
    def coming_soon_body(title, note=""):
        """A friendly placeholder for one of MY screens that isn't built yet
        (Share, Donate, Inbox, Settings)."""
        controls = [
            ft.Text("🚧", size=40),
            ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=BODY),
            ft.Text("This part of SharedPantry isn't built yet.", size=14, color=SECONDARY),
        ]
        if note:
            controls.append(ft.Text(note, size=13, color=SECONDARY,
                                    text_align=ft.TextAlign.CENTER))
        box = card(
            ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      spacing=10, controls=controls),
            padding=48,
        )
        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=720, spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(on_click=lambda e: app.navigate("my_pantry"),
                                 content=ft.Text("← Back to Shared Pantry", color=GREEN, size=14)),
                    box,
                ],
            ),
            alignment=ft.alignment.top_center,
        )

    # ----- "Kylee's screen — in progress" card ---------------------------
    def kylee_body(screen_name):
        """A clearly-labeled card for KYLEE'S screens (Home, Food IQ Scanner,
        Meal Planner, Recipe). I am not building these — they're Kylee's — so
        this card just says so. A blue border marks it as someone else's work."""
        box = ft.Container(
            bgcolor=CARD, border=ft.border.all(1.5, "#2B5FA3"),
            border_radius=RADIUS_CARD, padding=48,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
                controls=[
                    ft.Text("👩‍💻", size=40),
                    ft.Text("Kylee's screen — in progress", size=20,
                            weight=ft.FontWeight.BOLD, color="#2B5FA3"),
                    ft.Text(f'“{screen_name}” is being built by Kylee.',
                            size=14, color=BODY),
                    ft.Text("This isn't one of my screens — it's part of Kylee's "
                            "work, so it lives on her side of the app.",
                            size=13, color=SECONDARY, text_align=ft.TextAlign.CENTER),
                ],
            ),
        )
        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=720, spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[box],
            ),
            alignment=ft.alignment.top_center,
        )

    # ----- Impact page (real numbers computed from the database) ---------
    def impact_body():
        user = get_user(app.user_id)
        display_name = user["name"] if user else "Member"
        initial = (display_name[:1].upper() or "?")

        # "member since" from the account's join date, + how big the Circle is.
        since_txt = "new member"
        if user and user["joined_on"]:
            try:
                since_txt = "member since " + date.fromisoformat(user["joined_on"]).strftime("%b %Y")
            except ValueError:
                pass
        subtitle = f"{since_txt} \u00b7 Circle of {queries.get_circle_size(app.user_id)}"

        imp = queries.get_impact(app.user_id)      # the four numbers, from queries.py

        def do_logout(e):
            session.clear()                # forget the saved login
            app.user_id = None
            app.navigate("welcome")

        # --- profile header ---
        header_card = card(ft.Row(
            spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Text(initial, size=22, weight=ft.FontWeight.BOLD, color=GREEN),
                    width=56, height=56, bgcolor=GREEN_TINT, border_radius=999,
                    alignment=ft.alignment.center),
                ft.Column(expand=True, spacing=2, controls=[
                    ft.Text(display_name, size=22, weight=ft.FontWeight.BOLD, color=BODY),
                    ft.Text(subtitle, size=13.5, color=SECONDARY),
                ]),
                ft.Row(spacing=8, controls=[
                    secondary_button("\u2699 Settings", lambda e: app.navigate("settings")),
                    secondary_button("Log out", do_logout),
                ]),
            ],
        ))

        # --- the four Impact stat cards ---
        def stat_card(value, label, color):
            return ft.Container(
                expand=True, bgcolor=CARD, border_radius=RADIUS_CARD,
                border=ft.border.all(1, CARD_BORDER), padding=18,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
                    controls=[
                        ft.Text(value, size=30, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(label, size=13, color=SECONDARY, text_align=ft.TextAlign.CENTER),
                    ]))
        stats_row = ft.Row(spacing=14, controls=[
            stat_card(str(imp["meals_shared"]),  "meals shared",          GREEN_DARK),
            stat_card(str(imp["items_donated"]), "items donated",         "#2B5FA3"),
            stat_card(f'{imp["pounds_saved"]:.0f} lb',   "food saved from waste", "#C08A1D"),
            stat_card(f'\u2248 {imp["co2_avoided"]:.0f} lb', "CO\u2082 avoided",       "#2C5F3E"),
        ])

        # --- recent activity (shared / donated / requested, newest first) ---
        acts = queries.get_recent_activity(app.user_id)
        if acts:
            act_rows = [ft.Text(f'{emoji}  {text}  \u00b7  {when}', size=14, color=BODY)
                        for emoji, text, when in acts]
        else:
            act_rows = [ft.Text("No activity yet \u2014 share or donate something to see it here.",
                                size=14, color=SECONDARY)]
        activity_card = card(ft.Column(spacing=10, controls=[
            ft.Text("Recent activity", size=15, weight=ft.FontWeight.BOLD, color=BODY),
            ft.Column(spacing=8, controls=act_rows),
        ]))

        # --- badges: earned once you pass certain amounts ---
        badge_defs = [
            ("\U0001f91d", "First share",     imp["meals_shared"]  >= 1),
            ("\U0001f372", "Community cook",  imp["meals_shared"]  >= 5),
            ("\U0001f3e6", "Bank buddy",      imp["items_donated"] >= 1),
            ("\u267b\ufe0f", "Waste warrior", imp["pounds_saved"] >= 10),
            ("\U0001f30d", "Climate helper",  imp["co2_avoided"]   >= 25),
        ]
        badge_row = [ft.Text("Badges:", weight=ft.FontWeight.BOLD, color=BODY)]
        earned = [chip(f'{e}  {t}') for e, t, ok in badge_defs if ok]
        badge_row += earned if earned else [ft.Text("none yet", size=13, color=SECONDARY)]
        nxt = next((t for e, t, ok in badge_defs if not ok), None)
        if nxt:
            badge_row.append(ft.Container(
                content=ft.Text(f"next: {nxt}", size=12.5, weight=ft.FontWeight.BOLD, color="#8A8776"),
                border=ft.border.all(1.5, "#C6C2B2"), bgcolor=CARD,
                border_radius=999, padding=ft.Padding(12, 4, 12, 4)))
        badges_card = ft.Row(spacing=10, wrap=True,
                             vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=badge_row)

        return ft.Container(
            padding=ft.Padding(28, 22, 28, 32),
            content=ft.Column(
                width=980, spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    header_card, stats_row, activity_card, badges_card,
                ]),
            alignment=ft.alignment.top_center,
        )

    # ----- Welcome / login screen ----------------------------------------
    def welcome_body(mode):
        """The Welcome screen. It has two modes that toggle:
             "signin" -> email + password to log into an existing account
             "create" -> name + email + password to make a NEW account
        Layout matches design 01: a green brand panel on the LEFT and a white
        sign-in card on the RIGHT."""
        creating = (mode == "create")

        # A red line for friendly error messages (blank until something's wrong).
        err = ft.Text("", size=13, color="#B5402C")

        def make_field(hint, password=False):
            return ft.TextField(
                hint_text=hint, password=password, can_reveal_password=password,
                border_color=INPUT_BORDER, focused_border_color=GREEN,
                border_radius=RADIUS_INPUT, bgcolor=CARD, text_size=14,
                content_padding=ft.Padding(14, 12, 14, 12),
            )

        name_in  = make_field("Your name")
        email_in = make_field("Email…")
        pw_in    = make_field("Password…", password=True)

        def finish_login(uid):
            """Shared by sign-in and create: remember the user and go inside."""
            app.user_id = uid
            session.save(uid)          # so we stay logged in next time
            app.navigate("my_pantry")

        def submit(e):
            err.value = ""
            email = (email_in.value or "").strip()
            pw = pw_in.value or ""
            if creating:
                name = (name_in.value or "").strip()
                if not name or not email or not pw:
                    err.value = "Please fill in your name, email, and password."
                    err.update(); return
                if len(pw) < 4:
                    err.value = "Pick a password at least 4 characters long."
                    err.update(); return
                try:
                    uid = create_account(name, email, pw)
                except ValueError as ex:
                    err.value = str(ex); err.update(); return
                finish_login(uid)
            else:
                if not email or not pw:
                    err.value = "Please enter your email and password."
                    err.update(); return
                row = check_login(email, pw)
                if row is None:
                    err.value = "Hmm, that email or password isn't right."
                    err.update(); return
                finish_login(row["id"])

        def switch(e):
            # Flip to the other mode (redraws the Welcome screen).
            app.navigate("welcome", "signin" if creating else "create")

        # ----- LEFT: green brand panel -----
        brand_logo = ft.Row(
            spacing=12,
            controls=[
                ft.Container(
                    content=ft.Text("SP", size=18, weight=ft.FontWeight.BOLD, color=GREEN_DARK),
                    width=44, height=44, bgcolor="#FFFFFF", border_radius=12,
                    alignment=ft.alignment.center,
                ),
                ft.Text("SharedPantry", size=22, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ],
        )

        def brand_chip(text):
            return ft.Container(
                content=ft.Text(text, size=12.5, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                bgcolor=GREEN, border_radius=999, padding=ft.Padding(12, 6, 12, 6),
            )

        left = ft.Container(
            expand=True, bgcolor=GREEN_DARK, padding=48,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER, spacing=18,
                controls=[
                    brand_logo,
                    ft.Text("Know your food.\nWaste nothing.\nFeed your community.",
                            size=32, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ft.Text("Scan any food to check freshness & nutrition, track your "
                            "pantry, get recipe ideas — and pass on what you won't use "
                            "to friends, neighbors, and local food banks.",
                            size=14, color="#CBD8CC"),
                    ft.Row(wrap=True, spacing=8, controls=[
                        brand_chip("🔍 Food IQ Scanner"),
                        brand_chip("📦 Smart Pantry"),
                        brand_chip("🤝 Share & Donate"),
                    ]),
                ],
            ),
        )

        # ----- RIGHT: the sign-in / create-account card -----
        title = "Create your account" if creating else "Welcome back"
        button_label = "Create account" if creating else "Sign in"
        card_controls = [ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color=BODY)]
        if creating:
            card_controls.append(name_in)
        card_controls += [email_in, pw_in, err, primary_button(button_label, submit)]

        switch_prompt = ("Already have an account?" if creating else "New here?")
        switch_action = ("Sign in" if creating else "Create an account")
        card_controls.append(
            ft.Row(spacing=4, alignment=ft.MainAxisAlignment.CENTER, controls=[
                ft.Text(switch_prompt, size=13, color=SECONDARY),
                ft.Container(on_click=switch,
                             content=ft.Text(switch_action, size=13,
                                             weight=ft.FontWeight.BOLD, color=GREEN)),
            ])
        )

        right = ft.Container(
            expand=True, bgcolor=BG, padding=48, alignment=ft.alignment.center,
            content=ft.Container(
                width=380,
                content=card(
                    ft.Column(spacing=14,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                              controls=card_controls),
                    padding=28,
                ),
            ),
        )

        return ft.Row(
            spacing=0, height=640,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[left, right],
        )

    # ----- Add screen: reset the form, then show it ----------------------
    def add_screen(scanned=None):
        """Build the Add-to-Pantry form. Pass a scanned item dict to pre-fill
        it; with no argument it's a blank form. (Kylee's scanner will call
        app.navigate("add", {"name": ..., "best_by": ...}) — so the same form
        is reused; there is no hard-coded item anywhere.)"""
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
        return add_to_pantry_body(scanned)

    # ===================================================================
    # The routing table: turn a route name into the right screen body.
    # This is the ONE place that knows every screen. To add a screen later,
    # you build its *_body() function and add one line here.
    # ===================================================================
    def screen_for(route, arg):
        if route == "welcome":      return welcome_body(arg or "signin")
        if route == "my_pantry":    return pantry_body()
        if route == "add":          return add_screen(arg)
        if route == "item_options": return item_options_body(arg)
        if route == "impact":       return impact_body()
        if route == "share":        return share_body(arg)
        if route == "donate":       return donate_body(arg)
        if route == "food_bank_dashboard": return dashboard_body(arg)
        if route == "circle":       return circle_body()
        if route == "inbox":        return coming_soon_body(
            "Inbox", "Messages from your Circle will show up here (coming soon).")
        if route == "settings":     return coming_soon_body(
            "Settings", "You'll be able to edit your profile here later.")
        if route == "kylee":        return kylee_body(arg)
        # Unknown route -> fall back to the pantry so we're never stuck.
        return pantry_body()

    # Which top-bar tab lights up for each route (blank = no tab highlighted).
    ROUTE_TAB = {
        "my_pantry": "My Pantry", "add": "My Pantry", "item_options": "My Pantry",
        "share": "Share", "donate": "Donate", "circle": "My Circle",
        "impact": "Impact", "food_bank_dashboard": "Donate",
    }
    # Clicking a tab navigates to this route.
    TAB_ROUTE = {
        "My Pantry": "my_pantry", "Share": "share", "Donate": "donate",
        "My Circle": "circle", "Impact": "impact",
    }
    # Kylee's tabs (in the prototype's nav). They aren't built by us, so tapping
    # one shows the "Kylee's screen - in progress" card, with the tab's name.
    KYLEE_TABS = ["Home", "Food IQ Scanner"]

    def build_menu_bar(active_route):
        """The top menu bar: logo, the nav tabs (including Kylee's Home & Food IQ
        Scanner), an Inbox button, and the avatar. The tab matching the current
        screen is highlighted; clicking a tab or the avatar calls app.navigate."""
        active_tab = ROUTE_TAB.get(active_route, "")
        # On a Kylee screen, highlight whichever Kylee tab we're on (its name
        # is carried in app.arg).
        if active_route == "kylee":
            active_tab = app.arg
        # The avatar shows the logged-in user's first initial.
        me = get_user(app.user_id) if app.user_id else None
        my_initial = (me["name"][:1].upper() if me else "?")

        def tab(name):
            on = (name == active_tab)
            # A Kylee tab opens the "in progress" card; my own tabs go to my route.
            if name in KYLEE_TABS:
                click = lambda e, n=name: app.navigate("kylee", n)
            else:
                click = lambda e, r=TAB_ROUTE[name]: app.navigate(r)
            return ft.Container(
                content=ft.Text(name, size=15, weight=ft.FontWeight.BOLD,
                                color=GREEN_DARK if on else SECONDARY),
                bgcolor=GREEN_TINT if on else None,
                border_radius=999, padding=ft.Padding(16, 8, 16, 8),
                on_click=click,
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

        # Inbox button (no unread count until the real Inbox is built).
        inbox = ft.Container(
            content=ft.Text("💬 Inbox", size=14, weight=ft.FontWeight.BOLD,
                            color=GREEN_DARK),
            border=ft.border.all(1.5, GREEN), border_radius=RADIUS_INPUT,
            padding=ft.Padding(14, 8, 14, 8),
            on_click=lambda e: app.navigate("inbox"),
        )

        avatar = ft.Container(
            content=ft.Text(my_initial, weight=ft.FontWeight.BOLD, color=GREEN),
            width=38, height=38, bgcolor=GREEN_TINT, border_radius=999,
            alignment=ft.alignment.center,
            on_click=lambda e: app.navigate("impact"),   # avatar opens Profile
        )

        return ft.Container(
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, CARD_BORDER)),
            padding=ft.Padding(28, 14, 28, 14),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[logo, tabs, ft.Container(expand=True), inbox, avatar],
                spacing=18,
            ),
        )

    # Create the one controller for the whole app.
    app = App(page, screen_for, build_menu_bar)

    # ----- Daily auto-refresh --------------------------------------------
    # A tiny background helper wakes up every minute and, when the calendar
    # day changes (e.g. just after midnight), redraws the CURRENT screen so
    # every "days left" countdown drops by one on its own — no clicking needed.
    def watch_for_new_day():
        last_day = date.today()
        while True:
            time.sleep(60)
            today = date.today()
            if today != last_day:
                last_day = today
                try:
                    app.render()             # redraw current screen with fresh countdowns
                except Exception:
                    break                    # window closed — stop the helper

    threading.Thread(target=watch_for_new_day, daemon=True).start()

    # ----- Decide the first screen ---------------------------------------
    # If session.txt remembers a still-valid user, log them straight in and go
    # to the pantry. Otherwise (or if the saved id is stale), show Welcome.
    saved_id = session.load()
    if saved_id is not None and get_user(saved_id) is not None:
        app.user_id = saved_id
        app.navigate("my_pantry")
    else:
        session.clear()                 # tidy up a stale/leftover session
        app.navigate("welcome")


if __name__ == "__main__":
    ft.app(target=main)
