import flet as ft


def build_stat_card(title: str, line_one: str, line_two: str) -> ft.Container:
    # Shared card used for monthly impact metrics.
    return ft.Container(
        expand=True,
        bgcolor="#E6EFF3",
        border_radius=12,
        padding=14,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color="#2A2A2A"),
                ft.Text(line_one, size=32, weight=ft.FontWeight.BOLD, color="#111111"),
                ft.Text(line_two, size=16, weight=ft.FontWeight.W_600, color="#111111"),
            ],
        ),
    )


def build_nav_item(icon: str, label: str, selected: bool = False) -> ft.Column:
    # Bottom-nav item with a selected state style.
    icon_color = "#1AA87C" if selected else "#6E6E6E"
    text_color = "#1AA87C" if selected else "#6E6E6E"
    weight = ft.FontWeight.BOLD if selected else ft.FontWeight.W_500
    return ft.Column(
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(icon=icon, color=icon_color, size=24),
            ft.Text(label, size=12, color=text_color, weight=weight),
        ],
    )


def build_home_shell(metrics: dict, on_scan_click) -> ft.Container:
    # Home screen layout receives responsive metrics + navigation callback from MAIN.PY.
    content_padding = 24 if metrics["is_desktop"] else 18
    return ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor="#FFFFFF",
        border_radius=34,
        padding=ft.Padding(left=content_padding, top=22, right=content_padding, bottom=12),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color="#22000000",
            offset=ft.Offset(0, 8),
        ),
        content=ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    # Header block: app identity + top-right actions.
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            expand=True,
                            padding=ft.Padding(right=12, top=0, left=0, bottom=0),
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text(
                                        "PantryIQ Connect",
                                        size=metrics["title_size"],
                                        weight=ft.FontWeight.BOLD,
                                        color="#101010",
                                    ),
                                    ft.Text(
                                        "Scan Food, Understand Freshness,\n"
                                        "Collaborate, Donate and Reduce\n"
                                        "Waste Together!",
                                        size=metrics["subtitle_size"],
                                        color="#2B2B2B",
                                        weight=ft.FontWeight.W_500,
                                    ),
                                ],
                            ),
                        ),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.IconButton(icon=ft.Icons.SETTINGS, icon_color="#3A3A3A"),
                                ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE, icon_color="#3A3A3A"),
                            ],
                        ),
                    ],
                ),
                ft.Button(
                    # Primary call-to-action to open the barcode scanner screen.
                    "Scan Food",
                    width=None,
                    height=54,
                    on_click=on_scan_click,
                    style=ft.ButtonStyle(
                        bgcolor="#1AA87C",
                        color="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=27),
                        text_style=ft.TextStyle(size=metrics["button_text_size"], weight=ft.FontWeight.BOLD),
                    ),
                ),
                ft.Container(
                    # Goal tracker card replaces the previous placeholder area.
                    width=None,
                    padding=16,
                    border_radius=14,
                    bgcolor="#E9F8F2",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Text(
                                "Goal Tracker",
                                size=24 if metrics["is_desktop"] else 20,
                                weight=ft.FontWeight.BOLD,
                                color="#0D5F47",
                            ),
                            ft.Text(
                                "This month: Rescue 50 lbs of food",
                                size=14,
                                color="#2A2A2A",
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.ProgressBar(
                                value=0.64,
                                color="#1AA87C",
                                bgcolor="#CFEADF",
                                bar_height=10,
                                border_radius=10,
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        "32 lbs completed",
                                        size=13,
                                        color="#1F1F1F",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "64%",
                                        size=13,
                                        color="#0D5F47",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Text(
                    # Section label for monthly summary stats.
                    "Total Past Month",
                    size=metrics["section_title_size"],
                    weight=ft.FontWeight.BOLD,
                    color="#171717",
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        build_stat_card(
                            "No. of Pantry Items Shared/Donated",
                            "28 items",
                            "15 lbs",
                        ),
                        build_stat_card(
                            "No. of Food Composted",
                            "8 items",
                            "4 lbs",
                        ),
                    ],
                ),
                ft.Container(expand=True),
                ft.Divider(height=1, color="#DFE3E6"),
                ft.Row(
                    # Bottom navigation row (Home is active in this page).
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        build_nav_item(ft.Icons.HOME_ROUNDED, "Home", selected=True),
                        ft.GestureDetector(
                            on_tap=on_scan_click,
                            content=build_nav_item(ft.Icons.QR_CODE_SCANNER, "Scan"),
                        ),
                        build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry"),
                        build_nav_item(ft.Icons.PERSON_OUTLINE, "Me"),
                    ],
                ),
            ],
        ),
    )
