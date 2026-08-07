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


def _pantry_item(name: str, qty: str, freshness: str, days_left: str) -> ft.Container:
    return ft.Container(
        bgcolor="#F7FAFC",
        border_radius=14,
        padding=12,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(name, size=15, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                        ft.Text(f"Qty: {qty}", size=12, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    spacing=2,
                    controls=[
                        ft.Text(freshness, size=12, weight=ft.FontWeight.W_600, color=ThemeColors.GREEN_TEXT),
                        ft.Text(days_left, size=11, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
            ],
        ),
    )


def build_pantry_shell(metrics: dict, on_home_click, on_scan_click, on_me_click) -> ft.Container:
    """Render pantry dashboard with the same style language as home/scan."""

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
        build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", selected=True, compact=compact_nav),
        ft.GestureDetector(
            on_tap=on_me_click,
            content=build_nav_item(ft.Icons.PERSON_OUTLINE, "Me", compact=compact_nav),
        ),
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
                                "Pantry",
                                size=14,
                                color=ThemeColors.TEXT_SECONDARY,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                    ),
                    ft.IconButton(ft.Icons.TUNE, icon_color="#0F0F0F"),
                ],
            ),
        ),
        ft.Container(
            bgcolor="#DFEBDD",
            border_radius=18,
            padding=18,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text("Your Pantry", size=28 if metrics["is_desktop"] else 22, weight=ft.FontWeight.BOLD),
                            ft.Text("Track freshness and use older items first.", size=14, color=ThemeColors.TEXT_SECONDARY),
                        ],
                    ),
                    ft.Container(
                        bgcolor="#FFFFFF",
                        border_radius=12,
                        padding=ft.Padding(left=10, top=8, right=10, bottom=8),
                        content=ft.Text("24 Items", size=14, weight=ft.FontWeight.BOLD),
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
                    ft.Text("Needs Attention", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    _pantry_item("Greek Yogurt", "2", "Use soon", "1 day left"),
                    _pantry_item("Spinach", "1 bag", "Use soon", "2 days left"),
                    _pantry_item("Milk", "1", "Good", "4 days left"),
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
                    ft.Text("Storage Snapshot", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                expand=True,
                                border_radius=12,
                                bgcolor="#F7FAFC",
                                padding=10,
                                content=ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text("Fridge", size=12, color=ThemeColors.TEXT_SECONDARY),
                                        ft.Text("10 items", size=18, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                border_radius=12,
                                bgcolor="#F7FAFC",
                                padding=10,
                                content=ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text("Pantry", size=12, color=ThemeColors.TEXT_SECONDARY),
                                        ft.Text("9 items", size=18, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                border_radius=12,
                                bgcolor="#F7FAFC",
                                padding=10,
                                content=ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text("Freezer", size=12, color=ThemeColors.TEXT_SECONDARY),
                                        ft.Text("5 items", size=18, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                            ),
                        ],
                    ),
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
