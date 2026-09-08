"""Shared UI shell for PantryIQ Connect ported screens (Flet 0.85).

One place for the phone-style rounded shell, the top header, and the bottom nav,
so every ported page (Impact, Circle, Share, Donate, …) looks identical and there
is no copy-pasted layout code. Mirrors the look Nelson set up in pantry_page.py.

`active` selects which bottom-nav tab is highlighted: "home" | "scan" | "pantry"
| "me".  (Circle/Share/Donate/Impact currently ride under "me" until Nelson
decides their final place in the navigation.)
"""

from __future__ import annotations

import flet as ft

from pages.theme import ThemeColors as T


def nav_item(icon: ft.IconData, label: str, selected: bool, compact: bool) -> ft.Column:
    color = T.GREEN_TEXT if selected else T.TEXT_INACTIVE
    controls: list[ft.Control] = [ft.Icon(icon, color=color, size=24)]
    if not compact:
        controls.append(ft.Text(label, size=12, color=color,
                                weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500))
    return ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=controls)


def app_header(metrics: dict, subtitle: str, on_back=None) -> ft.Container:
    return ft.Container(
        bgcolor="#FFFFFF", border_radius=26, padding=ft.Padding(left=12, top=10, right=12, bottom=10),
        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, on_click=on_back) if on_back else ft.Container(width=40),
            ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text("PantryIQ Connect", size=24 if metrics["is_desktop"] else 18,
                        weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT),
                ft.Text(subtitle, size=14, color=T.TEXT_SECONDARY, weight=ft.FontWeight.W_600),
            ]),
            ft.Icon(ft.Icons.GROUP_OUTLINED, color=T.GREEN_TEXT, size=26),
        ]),
    )


def app_shell(metrics: dict, controls: list[ft.Control], active: str,
              on_home, on_scan, on_pantry, on_me) -> ft.Container:
    compact = metrics["shell_width"] < 360
    bottom = ft.Container(
        left=0, right=0, bottom=0, bgcolor="#FFFFFF",
        padding=ft.Padding(left=12, top=8, right=12, bottom=10),
        content=ft.Column(spacing=6, controls=[
            ft.Divider(height=1, color=T.DIVIDER),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[
                ft.GestureDetector(on_tap=on_home, content=nav_item(ft.Icons.HOME_ROUNDED, "Dashboard", active == "home", compact)),
                ft.GestureDetector(on_tap=on_scan, content=nav_item(ft.Icons.CAMERA_ALT_OUTLINED, "Scan Food", active == "scan", compact)),
                ft.GestureDetector(on_tap=on_pantry, content=nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", active == "pantry", compact)),
                ft.GestureDetector(on_tap=on_me, content=nav_item(ft.Icons.PERSON_OUTLINE, "Me", active == "me", compact)),
            ]),
        ]),
    )
    return ft.Container(
        width=metrics["shell_width"], height=metrics["shell_height"],
        bgcolor=T.GREEN_SURFACE, border_radius=34,
        padding=ft.Padding(left=14, top=16, right=14, bottom=0),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=30, color=T.SHELL_SHADOW, offset=ft.Offset(0, 8)),
        content=ft.Stack(controls=[
            ft.Column(spacing=T.SECTION_SPACING, scroll=ft.ScrollMode.AUTO, controls=controls + [ft.Container(height=82)]),
            bottom,
        ]),
    )
