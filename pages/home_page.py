import flet as ft

from pages.theme import ThemeColors


def build_stat_card(title: str, line_one: str, line_two: str) -> ft.Container:
    """Build one metric tile used in the monthly summary row.

    Args:
        title: Metric label shown in smaller text at the top of the card.
        line_one: Primary value (large number) for fast visual scanning.
        line_two: Secondary unit/context value shown under the primary value.
    """

    # Shared card used for monthly impact metrics.
    # `expand=True` lets two cards split available row space evenly.
    return ft.Container(
        expand=True,
        bgcolor=ThemeColors.CARD_BACKGROUND,
        border_radius=12,
        padding=14,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=ThemeColors.TEXT_SECONDARY),
                ft.Text(line_one, size=32, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                ft.Text(line_two, size=16, weight=ft.FontWeight.W_600, color=ThemeColors.TEXT_PRIMARY),
            ],
        ),
    )


def build_nav_item(icon: ft.IconData, label: str, selected: bool = False) -> ft.Column:
    """Return a bottom navigation item with active/inactive visual state.

    The selected item uses brand color and bolder typography to establish
    current location while unselected items remain muted.
    """

    # Bottom-nav item with a selected state style.
    # Color + weight are derived from one `selected` flag for consistency.
    icon_color = ThemeColors.BRAND_PRIMARY if selected else ThemeColors.TEXT_INACTIVE
    text_color = ThemeColors.BRAND_PRIMARY if selected else ThemeColors.TEXT_INACTIVE
    weight = ft.FontWeight.BOLD if selected else ft.FontWeight.W_500
    nav_item_controls: list[ft.Control] = [
        ft.Icon(icon=icon, color=icon_color, size=24),
        ft.Text(label, size=12, color=text_color, weight=weight),
    ]
    return ft.Column(
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=nav_item_controls,
    )


def build_home_shell(metrics: dict, on_scan_click) -> ft.Container:
    """Compose the full home screen shell used by the main renderer.

    Args:
        metrics: Responsive sizing map from MAIN.PY (breakpoint-derived).
        on_scan_click: Navigation callback that switches to scan view.
    """

    # Home screen layout receives responsive metrics + navigation callback from MAIN.PY.
    # Desktop gets slightly wider horizontal breathing room for longer lines.
    content_padding = 24 if metrics["is_desktop"] else 18
    bottom_nav_controls: list[ft.Control] = [
        build_nav_item(ft.Icons.HOME_ROUNDED, "Home", selected=True),
        ft.GestureDetector(
            on_tap=on_scan_click,
            content=build_nav_item(ft.Icons.QR_CODE_SCANNER, "Scan"),
        ),
        build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry"),
        build_nav_item(ft.Icons.PERSON_OUTLINE, "Me"),
    ]

    home_controls: list[ft.Control] = [
        ft.Row(
            # Header block: app identity + top-right actions.
            # Left side expands so title/subtitle can wrap naturally while
            # action icons stay anchored to the right edge.
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
                                color=ThemeColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Scan Food, Understand Freshness,\n"
                                "Collaborate, Donate and Reduce\n"
                                "Waste Together!",
                                size=metrics["subtitle_size"],
                                color=ThemeColors.TEXT_SECONDARY,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                    ),
                ),
                ft.Row(
                    # Placeholder utility actions (settings/alerts).
                    # Kept presentational for now until action handlers are added.
                    spacing=4,
                    controls=[
                        ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=ThemeColors.TEXT_TERTIARY),
                        ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE, icon_color=ThemeColors.TEXT_TERTIARY),
                    ],
                ),
            ],
        ),
        ft.Button(
            # Primary call-to-action to open the barcode scanner screen.
            # This is intentionally large and central to establish the
            # app's main task as the first action.
            "Scan Food",
            width=None,
            height=54,
            on_click=on_scan_click,
            style=ft.ButtonStyle(
                bgcolor=ThemeColors.BRAND_PRIMARY,
                color=ThemeColors.BRAND_ON_PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=27),
                text_style=ft.TextStyle(size=metrics["button_text_size"], weight=ft.FontWeight.BOLD),
            ),
        ),
        ft.Container(
            # Goal tracker card replaces the previous placeholder area.
            # Uses progress + explicit ratio text so status is still
            # understandable for users who cannot rely on color alone.
            width=None,
            padding=16,
            border_radius=14,
            bgcolor=ThemeColors.TRACKER_BACKGROUND,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        "Goal Tracker",
                        size=24 if metrics["is_desktop"] else 20,
                        weight=ft.FontWeight.BOLD,
                        color=ThemeColors.TRACKER_TEXT,
                    ),
                    ft.Text(
                        "This month: Rescue 50 lbs of food",
                        size=14,
                        color=ThemeColors.TEXT_SECONDARY,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.ProgressBar(
                        value=0.64,
                        color=ThemeColors.BRAND_PRIMARY,
                        bgcolor=ThemeColors.PROGRESS_TRACK,
                        bar_height=10,
                        border_radius=10,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "32 lbs completed",
                                size=13,
                                color=ThemeColors.TEXT_SECONDARY,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "64%",
                                size=13,
                                color=ThemeColors.TRACKER_TEXT,
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
            color=ThemeColors.TEXT_SECONDARY,
        ),
        ft.Row(
            # Two-card snapshot for monthly impact categories.
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
        ft.Divider(height=1, color=ThemeColors.DIVIDER),
        ft.Row(
            # Bottom navigation row (Home is active in this page).
            # Scan item is interactive here to mirror the primary CTA.
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            controls=bottom_nav_controls,
        ),
    ]

    return ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor=ThemeColors.SHELL_BACKGROUND,
        border_radius=34,
        padding=ft.Padding(left=content_padding, top=22, right=content_padding, bottom=12),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color=ThemeColors.SHELL_SHADOW,
            offset=ft.Offset(0, 8),
        ),
        content=ft.Column(
            expand=True,
            spacing=16,
            controls=home_controls,
        ),
    )
