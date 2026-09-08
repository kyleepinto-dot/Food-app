"""Donate flow + food-bank dashboard for PantryIQ Connect (ported from Yaashvi's app).

Donate is a 3-step flow on one screen:
  1. Eligibility (only sealed, in-date items qualify — db.can_donate) + pick an item
  2. Pick a partner food bank
  3. Confirm the drop-off and get a pass
Plus a partner dashboard where a food bank checks donations in.

Flet 0.85, shared shell, UI only. MAIN.PY owns the selection state and passes the
current selection in; the pick/confirm callbacks update it and re-render.

Donate data contract:
  data = {
    "eligible": list[dict],   # id, name, qty
    "banks": list[dict],      # id, name, distance_mi, accepts, schedule
    "selected_item_id": int|None, "selected_bank_id": int|None,
    "reason": str|None,       # ineligibility banner when arriving from a bad item
    "pass": dict|None,        # created pass: id, title, bank, window, bank_id
  }
Callbacks: on_pick_item(id), on_pick_bank(id), on_confirm(), on_view_dashboard(bank_id)
"""

from __future__ import annotations

import flet as ft

from pages.theme import ThemeColors as T
from pages.shell_kit import app_shell, app_header

CHECKLIST = [
    ("Sealed / unopened packaging", True),
    ('Before "best by" date', True),
    ("Ingredient label intact", True),
    ("Not homemade or reheated", False),
    ("No damaged / bulging cans", False),
]


def _step_header(n: int, title: str) -> ft.Column:
    return ft.Column(spacing=8, controls=[
        ft.Container(bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
                     padding=ft.Padding(left=12, top=4, right=12, bottom=4),
                     content=ft.Text(f"STEP {n}", size=12, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT)),
        ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
    ])


def _card(controls: list[ft.Control]) -> ft.Container:
    return ft.Container(bgcolor="#FFFFFF", border=ft.Border.all(1, "#E1E7E2"),
                        border_radius=18, padding=16,
                        content=ft.Column(spacing=12, controls=controls))


def _qr_box() -> ft.Container:
    return ft.Container(width=150, height=150, bgcolor="#EFEDE5", border_radius=12,
                        border=ft.Border.all(1.5, "#BDB9A9"), alignment=ft.Alignment(0, 0),
                        content=ft.Text("QR code", size=12, color="#8A8776"))


def build_donate_shell(
    metrics: dict, data: dict, on_pick_item, on_pick_bank, on_confirm, on_view_dashboard,
    on_home_click, on_scan_click, on_pantry_click, on_me_click, on_back_click=None,
) -> ft.Container:
    """Render the 3-step Donate flow. UI only; MAIN.PY owns selection + writes."""
    eligible = data.get("eligible") or []
    banks = data.get("banks") or []
    sel_item = next((it for it in eligible if it["id"] == data.get("selected_item_id")), None)
    sel_bank = next((b for b in banks if b["id"] == data.get("selected_bank_id")), None)
    created = data.get("pass")

    # STEP 1 — eligibility + item pick
    step1 = [_step_header(1, "Does it qualify?")]
    step1 += [ft.Row(spacing=8, controls=[
        ft.Text("✅" if ok else "☐", size=14),
        ft.Text(text, size=13, color=T.TEXT_PRIMARY if ok else T.TEXT_SECONDARY),
    ]) for text, ok in CHECKLIST]
    if data.get("reason"):
        step1.append(ft.Container(bgcolor="#FAF7EC", border=ft.Border.all(1, "#E6D5A8"),
                                  border_radius=12, padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                                  content=ft.Text(str(data["reason"]), size=13, color="#8F6410")))
    step1.append(ft.Text("Choose an item to donate", size=13, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY))
    if eligible:
        for it in eligible:
            chosen = bool(sel_item and it["id"] == sel_item["id"])
            qty = int(it.get("qty") or 1)
            step1.append(ft.Container(
                on_click=lambda _, i=it["id"]: on_pick_item(i),
                bgcolor=T.GREEN_SURFACE_SOFT if chosen else "#FFFFFF",
                border=ft.Border.all(1.5 if chosen else 1, T.BRAND_PRIMARY if chosen else "#E1E7E2"),
                border_radius=12, padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                content=ft.Text(f"{it.get('name')}" + (f" ×{qty}" if qty > 1 else ""),
                                size=14, weight=ft.FontWeight.BOLD,
                                color=T.GREEN_TEXT if chosen else T.TEXT_PRIMARY)))
    else:
        step1.append(ft.Text("You have no sealed, in-date items to donate right now.",
                             size=13, color=T.TEXT_SECONDARY))

    # STEP 2 — pick a bank
    step2 = [_step_header(2, "Pick a food bank")]
    for b in banks:
        chosen = bool(sel_bank and b["id"] == sel_bank["id"])
        step2.append(ft.Container(
            on_click=lambda _, i=b["id"]: on_pick_bank(i),
            bgcolor="#FFFFFF", border=ft.Border.all(2 if chosen else 1, "#2B5FA3" if chosen else "#E1E7E2"),
            border_radius=14, padding=14,
            content=ft.Column(spacing=2, controls=[
                ft.Text(("◉ " if chosen else "○ ") + str(b.get("name")), size=15,
                        weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                ft.Text(f"{b.get('distance_mi')} mi · needs: {b.get('accepts')} · {b.get('schedule')}",
                        size=13, color=T.TEXT_SECONDARY),
            ])))

    # STEP 3 — pass
    step3 = [_step_header(3, "Your drop-off pass")]
    if created:
        step3.append(_card([
            ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, controls=[
                _qr_box(),
                ft.Text(f"Donation #{int(created['id']):04d}", size=17, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                ft.Text(f"{created.get('title')} · {created.get('bank')}", size=13,
                        color=T.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{created.get('window')} · show at desk", size=13, color=T.TEXT_SECONDARY),
                ft.Container(on_click=lambda _, i=created.get("bank_id"): on_view_dashboard(i),
                             content=ft.Text(f"View {created.get('bank')} dashboard →",
                                             color=T.GREEN_TEXT, size=13, weight=ft.FontWeight.BOLD)),
            ]),
        ]))
    elif sel_item and sel_bank:
        qty = int(sel_item.get("qty") or 1)
        step3.append(_card([
            ft.Text(f"{sel_item.get('name')}" + (f" ×{qty}" if qty > 1 else ""),
                    size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            ft.Text(f"{sel_bank.get('name')} · {sel_bank.get('schedule')}", size=13, color=T.TEXT_SECONDARY),
            ft.Button(content=ft.Text("Confirm drop-off slot", weight=ft.FontWeight.BOLD),
                      on_click=lambda _: on_confirm(),
                      style=ft.ButtonStyle(bgcolor=T.BRAND_PRIMARY, color="#FFFFFF",
                                           shape=ft.RoundedRectangleBorder(radius=13))),
        ]))
    else:
        step3.append(ft.Text("Pick an item and a food bank to get your drop-off pass.",
                             size=13, color=T.TEXT_SECONDARY))

    controls = [
        app_header(metrics, "Donate to a food bank", on_back_click),
        _card(step1), _card(step2), _card(step3),
    ]
    return app_shell(metrics, controls, "me", on_home_click, on_scan_click, on_pantry_click, on_me_click)


def build_dashboard_shell(
    metrics: dict, bank: dict, incoming: list, on_check_in,
    on_home_click, on_scan_click, on_pantry_click, on_me_click, on_back_click=None,
) -> ft.Container:
    """Food-bank partner dashboard: list incoming donations and check them in."""
    rows: list[ft.Control] = []
    for d in incoming or []:
        checked = str(d.get("status")) == "checked_in"
        qty = int(d.get("qty") or 1)
        right = (ft.Text("✓ checked in", size=13, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT) if checked
                 else ft.Button(content=ft.Text("Check in", size=12), on_click=lambda _, i=d["id"]: on_check_in(i),
                                style=ft.ButtonStyle(bgcolor=T.BRAND_PRIMARY, color="#FFFFFF",
                                                     shape=ft.RoundedRectangleBorder(radius=12))))
        rows.append(ft.Container(
            bgcolor="#FFFFFF", border=ft.Border.all(1, "#E1E7E2"), border_radius=14, padding=14,
            content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Container(bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
                             padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                             content=ft.Text(f"#{int(d['id']):04d}", size=12, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT)),
                ft.Column(expand=True, spacing=2, controls=[
                    ft.Text(f"{d.get('item_name')}" + (f" ×{qty}" if qty > 1 else ""),
                            size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                    ft.Text(f"{d.get('donor_name')} · verified sealed & in-date ✓", size=13, color=T.TEXT_SECONDARY),
                ]),
                right,
            ]),
        ))
    if not rows:
        rows = [ft.Text("No incoming donations yet.", size=13, color=T.TEXT_SECONDARY)]

    need_chips = [ft.Container(bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
                              padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                              content=ft.Text(n.strip(), size=12, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT))
                 for n in str(bank.get("accepts") or "").split(",") if n.strip()]

    controls = [
        app_header(metrics, str(bank.get("name") or "Food bank"), on_back_click),
        ft.Container(bgcolor="#FFFFFF", border_radius=18, padding=16, content=ft.Column(spacing=12, controls=[
            ft.Text(f"Incoming donations ({bank.get('schedule')})", size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            *rows,
        ])),
        ft.Container(bgcolor="#FFFFFF", border_radius=18, padding=16, content=ft.Column(spacing=10, controls=[
            ft.Text("Current needs", size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            ft.Row(wrap=True, spacing=8, run_spacing=8, controls=need_chips),
            ft.Text("These needs show up on members' Donate screens.", size=13, color=T.TEXT_SECONDARY),
        ])),
    ]
    return app_shell(metrics, controls, "me", on_home_click, on_scan_click, on_pantry_click, on_me_click)
