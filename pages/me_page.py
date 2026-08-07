import flet as ft

from pages.theme import ThemeColors


def build_nav_item(icon: ft.IconData, label: str, selected: bool = False, compact: bool = False) -> ft.Column:
    """Return a bottom navigation item with active/inactive visual state."""

    icon_color = "#2E5D4E" if selected else ThemeColors.TEXT_INACTIVE
    text_color = "#2E5D4E" if selected else ThemeColors.TEXT_INACTIVE
    weight = ft.FontWeight.BOLD if selected else ft.FontWeight.W_500
    nav_item_controls: list[ft.Control] = [ft.Icon(icon=icon, color=icon_color, size=24)]
    if not compact:
        nav_item_controls.append(ft.Text(label, size=12, color=text_color, weight=weight))

    return ft.Column(
        spacing=2 if not compact else 0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=nav_item_controls,
    )


def _profile_metric(label: str, value: str) -> ft.Container:
    return ft.Container(
        expand=True,
        bgcolor="#F7FAFC",
        border_radius=12,
        padding=10,
        content=ft.Column(
            spacing=2,
            controls=[
                ft.Text(label, size=12, color=ThemeColors.TEXT_SECONDARY),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
            ],
        ),
    )


def _setting_row(icon: ft.IconData, label: str, helper: str) -> ft.Container:
    return ft.Container(
        bgcolor="#F7FAFC",
        border_radius=12,
        padding=10,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(icon, size=16, color=ThemeColors.GREEN_TEXT),
                        ft.Column(
                            spacing=1,
                            controls=[
                                ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=ThemeColors.TEXT_PRIMARY),
                                ft.Text(helper, size=11, color=ThemeColors.TEXT_SECONDARY),
                            ],
                        ),
                    ],
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=ThemeColors.TEXT_INACTIVE),
            ],
        ),
    )


def build_me_shell(metrics: dict, on_home_click, on_scan_click, on_pantry_click) -> ft.Container:
    """Render account/profile page using the same visual language as app screens."""

    compact_nav = metrics["shell_width"] < 360

    bottom_nav_controls: list[ft.Control] = [
        ft.GestureDetector(
            on_tap=on_home_click,
            content=build_nav_item(ft.Icons.HOME_ROUNDED, "Dashboard", compact=compact_nav),
        ),
        ft.GestureDetector(
            on_tap=on_scan_click,
            content=build_nav_item(ft.Icons.CAMERA_ALT_OUTLINED, "Scan Food", compact=compact_nav),
        ),
        ft.GestureDetector(
            on_tap=on_pantry_click,
            content=build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", compact=compact_nav),
        ),
        build_nav_item(ft.Icons.PERSON_OUTLINE, "Me", selected=True, compact=compact_nav),
    ]

    content_controls: list[ft.Control] = [
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=26,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=36),
                    ft.Column(
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                "PantryIQ Connect",
                                size=24 if metrics["is_desktop"] else 18,
                                weight=ft.FontWeight.BOLD,
                                color=ThemeColors.GREEN_TEXT,
                            ),
                            ft.Text(
                                "Me",
                                size=14,
                                color=ThemeColors.TEXT_SECONDARY,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                    ),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color="#0F0F0F"),
                ],
            ),
        ),
        ft.Container(
            bgcolor="#DFEBDD",
            border_radius=18,
            padding=18,
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=64,
                        height=64,
                        border_radius=32,
                        bgcolor="#FFFFFF",
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.PERSON, size=34, color=ThemeColors.GREEN_TEXT),
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("Jamie Carter", size=22 if metrics["is_desktop"] else 18, weight=ft.FontWeight.BOLD),
                            ft.Text("Community Member", size=13, color=ThemeColors.TEXT_SECONDARY),
                            ft.Text("Keeping food fresh, sharing what I can.", size=12, color=ThemeColors.TEXT_SECONDARY),
                        ],
                    ),
                ],
            ),
        ),
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("My Impact", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    ft.Row(
                        spacing=8,
                        controls=[
                            _profile_metric("Scans", "184"),
                            _profile_metric("Pantry Items", "24"),
                            _profile_metric("Food Saved", "128 lbs"),
                        ],
                    ),
                ],
            ),
        ),
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("Settings", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    _setting_row(ft.Icons.NOTIFICATIONS_NONE, "Notifications", "Expiry reminders and scan updates"),
                    _setting_row(ft.Icons.LANGUAGE, "Language", "English (US)"),
                    _setting_row(ft.Icons.PRIVACY_TIP_OUTLINED, "Privacy", "Manage shared data preferences"),
                    _setting_row(ft.Icons.HELP_OUTLINE_ROUNDED, "Help & Support", "FAQs and contact options"),
                ],
            ),
        ),
        ft.Container(height=74),
    ]

    bottom_nav_bar = ft.Container(
        left=0,
        right=0,
        bottom=0,
        bgcolor="#FFFFFF",
        padding=ft.Padding(left=12, top=8, right=12, bottom=10),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Divider(height=1, color=ThemeColors.DIVIDER),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=bottom_nav_controls,
                ),
            ],
        ),
    )

    return ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor=ThemeColors.GREEN_SURFACE,
        border_radius=34,
        padding=ft.Padding(left=14, top=16, right=14, bottom=0),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color=ThemeColors.SHELL_SHADOW,
            offset=ft.Offset(0, 8),
        ),
        content=ft.Stack(
            controls=[
                ft.Column(
                    spacing=ThemeColors.SECTION_SPACING,
                    scroll=ft.ScrollMode.AUTO,
                    controls=content_controls,
                ),
                bottom_nav_bar,
            ],
        ),
    )
