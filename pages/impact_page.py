"""Impact / Profile screen for PantryIQ Connect (ported from Yaashvi's app).

Ported into the single app's Flet 0.85 design language, using the shared shell in
shell_kit.py and the `build_*_shell(metrics, data, callbacks)` pattern from
pantry_page.py. UI only — MAIN.PY computes the data and passes it in.

Data contract:
  profile  = {"name": str, "since_text": str, "circle_size": int}
  stats    = {"meals_shared": int, "items_donated": int,
              "pounds_saved": float, "co2_avoided": float}
  activity = list[tuple[str, str, str]]   # (emoji, text, when)

Nav placement (Impact under "Me") is a placeholder pending Nelson's call.
"""

from __future__ import annotations

import flet as ft

from pages.theme import ThemeColors as T
from pages.shell_kit import app_shell, app_header


def _stat_card(value: str, label: str, color: str) -> ft.Container:
    return ft.Container(
        expand=True, bgcolor="#FFFFFF", border_radius=16, padding=16,
        border=ft.Border.all(1, "#E1E7E2"),
        content=ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Text(value, size=26, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(label, size=12, color=T.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
        ]),
    )


def build_impact_shell(
    metrics: dict, profile: dict, stats: dict, activity: list,
    on_home_click, on_scan_click, on_pantry_click, on_me_click,
    on_logout, on_settings=None, on_back_click=None, on_circle=None,
) -> ft.Container:
    """Render the Impact / profile screen. UI only; data is passed in."""
    name = str(profile.get("name") or "Member")
    initial = (name[:1].upper() or "?")
    subtitle = f"{profile.get('since_text', 'new member')} · Circle of {int(profile.get('circle_size') or 0)}"

    meals = int(stats.get("meals_shared") or 0)
    donated = int(stats.get("items_donated") or 0)
    pounds = float(stats.get("pounds_saved") or 0)
    co2 = float(stats.get("co2_avoided") or 0)

    header_card = ft.Container(
        bgcolor="#FFFFFF", border_radius=18, padding=16,
        content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Container(width=56, height=56, bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
                         alignment=ft.Alignment(0, 0),
                         content=ft.Text(initial, size=22, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT)),
            ft.Column(expand=True, spacing=2, controls=[
                ft.Text(name, size=20, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                ft.Text(subtitle, size=13, color=T.TEXT_SECONDARY),
            ]),
            ft.Button(content=ft.Text("My Circle"), on_click=lambda _: on_circle(),
                      style=ft.ButtonStyle(bgcolor=T.GREEN_SURFACE_SOFT, color=T.GREEN_TEXT,
                                           shape=ft.RoundedRectangleBorder(radius=12))) if on_circle else ft.Container(),
            ft.IconButton(ft.Icons.SETTINGS_OUTLINED, icon_color=T.GREEN_TEXT,
                          on_click=on_settings) if on_settings else ft.Container(),
            ft.Button(content=ft.Text("Log out"), on_click=on_logout,
                      style=ft.ButtonStyle(bgcolor="#FFF7E5", color="#8F6410",
                                           shape=ft.RoundedRectangleBorder(radius=12))),
        ]),
    )

    stats_grid = ft.Column(spacing=10, controls=[
        ft.Row(spacing=10, controls=[
            _stat_card(str(meals), "meals shared", T.GREEN_TEXT),
            _stat_card(str(donated), "items donated", "#2B5FA3"),
        ]),
        ft.Row(spacing=10, controls=[
            _stat_card(f"{pounds:.0f} lb", "food saved from waste", "#C08A1D"),
            _stat_card(f"≈ {co2:.0f} lb", "CO₂ avoided", "#2C5F3E"),
        ]),
    ])

    if activity:
        act_rows = [ft.Text(f"{emoji}  {text}  ·  {when}", size=13, color=T.TEXT_PRIMARY)
                    for emoji, text, when in activity]
    else:
        act_rows = [ft.Text("No activity yet — share or donate something to see it here.",
                            size=13, color=T.TEXT_SECONDARY)]
    activity_card = ft.Container(
        bgcolor="#FFFFFF", border_radius=18, padding=16,
        content=ft.Column(spacing=10, controls=[
            ft.Text("Recent activity", size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            ft.Column(spacing=8, controls=act_rows),
        ]),
    )

    badge_defs = [
        ("🤝", "First share", meals >= 1),
        ("🍲", "Community cook", meals >= 5),
        ("🏦", "Bank buddy", donated >= 1),
        ("♻️", "Waste warrior", pounds >= 10),
        ("🌍", "Climate helper", co2 >= 25),
    ]
    badge_chips: list[ft.Control] = [ft.Text("Badges:", weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY)]
    earned = [ft.Container(bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
                           padding=ft.Padding(left=12, top=4, right=12, bottom=4),
                           content=ft.Text(f"{e}  {t}", size=12, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT))
              for e, t, ok in badge_defs if ok]
    badge_chips += earned or [ft.Text("none yet", size=13, color=T.TEXT_SECONDARY)]
    nxt = next((t for e, t, ok in badge_defs if not ok), None)
    if nxt:
        badge_chips.append(ft.Container(
            bgcolor="#FFFFFF", border=ft.Border.all(1.5, "#C6C2B2"), border_radius=999,
            padding=ft.Padding(left=12, top=4, right=12, bottom=4),
            content=ft.Text(f"next: {nxt}", size=12, weight=ft.FontWeight.BOLD, color="#8A8776")))
    badges_card = ft.Container(
        bgcolor="#FFFFFF", border_radius=18, padding=16,
        content=ft.Row(wrap=True, spacing=8, run_spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=badge_chips),
    )

    controls = [
        app_header(metrics, "Your Impact", on_back_click),
        header_card, stats_grid, activity_card, badges_card,
    ]
    return app_shell(metrics, controls, "me", on_home_click, on_scan_click, on_pantry_click, on_me_click)
