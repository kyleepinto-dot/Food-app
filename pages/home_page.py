import flet as ft

from pages.theme import ThemeColors


def build_stat_card(title: str, line_one: str, line_two: str, expand: bool = True) -> ft.Container:
    """Build one metric tile used in the monthly summary row.

    Args:
        title: Metric label shown in smaller text at the top of the card.
        line_one: Primary value (large number) for fast visual scanning.
        line_two: Secondary unit/context value shown under the primary value.
    """

    # Shared card used for monthly impact metrics.
    # `expand=True` lets two cards split available row space evenly.
    return ft.Container(
        expand=expand,
        bgcolor=ThemeColors.ACCENT_YELLOW_SUBTLE,
        border_radius=ThemeColors.CARD_RADIUS_INNER,
        padding=ThemeColors.CARD_PADDING,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=ThemeColors.TEXT_SECONDARY),
                ft.Text(line_one, size=32, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                ft.Text(line_two, size=16, weight=ft.FontWeight.W_600, color=ThemeColors.TEXT_PRIMARY),
            ],
        ),
    )


def build_nav_item(icon: ft.IconData, label: str, selected: bool = False, compact: bool = False) -> ft.Column:
    """Return a bottom navigation item with active/inactive visual state.

    The selected item uses brand color and bolder typography to establish
    current location while unselected items remain muted.
    """

    # Bottom-nav item with a selected state style.
    # Color + weight are derived from one `selected` flag for consistency.
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


def build_home_shell(
    metrics: dict,
    on_scan_click,
    on_pantry_click,
    on_me_click,
    recent_products: list[dict] | None = None,
    on_recent_product_click=None,
    profile: dict | None = None,
) -> ft.Container:
    """Compose the full home screen shell used by the main renderer.

    Args:
        metrics: Responsive sizing map from MAIN.PY (breakpoint-derived).
        on_scan_click: Navigation callback that switches to scan view.
    """

    content_padding = 18 if metrics["is_desktop"] else 14
    compact_nav = metrics["shell_width"] < 360
    profile_data = profile or {}
    scan_count = int(profile_data.get("scan_count") or 0)
    pantry_item_count = int(profile_data.get("pantry_item_count") or 0)
    food_saved_lbs = float(profile_data.get("food_saved_lbs") or 0)

    def info_tile(title: str, value: str, subtitle: str, icon: ft.IconData) -> ft.Container:
        return ft.Container(
            expand=True,
            padding=10,
            border_radius=12,
            bgcolor="#F8FAFC",
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.Icon(icon, size=14, color=ThemeColors.GREEN_TEXT),
                            ft.Text(title, size=11, color=ThemeColors.TEXT_SECONDARY),
                        ],
                    ),
                    ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    ft.Text(subtitle, size=11, color=ThemeColors.TEXT_SECONDARY),
                ],
            ),
        )

    def community_impact_card() -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=12,
            content=ft.Column(
                expand=True,
                spacing=10,
                controls=[
                    ft.Text("Community Impact", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    ft.Row(
                        spacing=8,
                        controls=[
                            info_tile("Meals Supported", "1,248", "+18% vs last month", ft.Icons.RESTAURANT_MENU),
                            info_tile("Food Donated", "523 lbs", "+22% vs last month", ft.Icons.FAVORITE_BORDER),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            info_tile("Food Composted", "213 lbs", "+10% vs last month", ft.Icons.ECO_OUTLINED),
                            info_tile("CO2e Avoided", "1,152 lbs", "+20% vs last month", ft.Icons.CLOUD_QUEUE),
                        ],
                    ),
                ],
            ),
        )

    def top_categories_card() -> ft.Container:
        def category_row(name: str, color: str) -> ft.Row:
            return ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(width=10, height=10, border_radius=5, bgcolor=color),
                            ft.Text(name, size=13, color=ThemeColors.TEXT_SECONDARY),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=ThemeColors.TEXT_INACTIVE),
                ],
            )

        return ft.Container(
            expand=True,
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=12,
            content=ft.Column(
                expand=True,
                spacing=10,
                controls=[
                    ft.Text("Top Categories", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    category_row("Produce", "#2F7D32"),
                    category_row("Dairy", "#84A98C"),
                    category_row("Grains", "#F0B429"),
                    category_row("Proteins", "#5F8AA1"),
                    category_row("Other", "#D4D4D4"),
                ],
            ),
        )

    def challenge_row(title: str, dates: str) -> ft.Container:
        return ft.Container(
            padding=ft.Padding(left=0, top=4, right=0, bottom=4),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.FAVORITE_BORDER, size=15, color=ThemeColors.TEXT_SECONDARY),
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text(title, size=12, weight=ft.FontWeight.W_600, color=ThemeColors.TEXT_PRIMARY),
                                    ft.Text(dates, size=10, color=ThemeColors.TEXT_SECONDARY),
                                ],
                            ),
                        ],
                    ),
                    ft.Button(
                        "Join",
                        style=ft.ButtonStyle(
                            bgcolor="#FFFFFF",
                            color=ThemeColors.TEXT_PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    ),
                ],
            ),
        )

    def challenges_card() -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=12,
            content=ft.Column(
                expand=True,
                spacing=8,
                controls=[
                    ft.Text("Community Challenges", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                    challenge_row("Zero Waste Week", "May 20 - May 26"),
                    challenge_row("Share More, Waste Less", "Jun 1 - Jun 7"),
                    ft.Container(
                        alignment=ft.Alignment(0, 0),
                        content=ft.Button(
                            "View All Challenges",
                            style=ft.ButtonStyle(
                                bgcolor="#FFFFFF",
                                color=ThemeColors.TEXT_PRIMARY,
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                        ),
                    ),
                ],
            ),
        )

    bottom_nav_controls: list[ft.Control] = [
        build_nav_item(ft.Icons.HOME_ROUNDED, "Dashboard", selected=True, compact=compact_nav),
        ft.GestureDetector(
            on_tap=on_scan_click,
            content=build_nav_item(ft.Icons.CAMERA_ALT_OUTLINED, "Scan Food", compact=compact_nav),
        ),
        ft.GestureDetector(
            on_tap=on_pantry_click,
            content=build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", compact=compact_nav),
        ),
        ft.GestureDetector(
            on_tap=on_me_click,
            content=build_nav_item(ft.Icons.PERSON_OUTLINE, "Me", compact=compact_nav),
        ),
    ]

    hero_banner = ft.Container(
        bgcolor="#DFEBDD",
        border_radius=18,
        padding=18,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Text("Scan Food. Understand Freshness.", size=28 if metrics["is_desktop"] else 22, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Collaborate, Donate and Reduce Waste\nTogether!",
                                size=15,
                                color=ThemeColors.TEXT_SECONDARY,
                            ),
                            ft.Button(
                                content=ft.Row(
                                    tight=True,
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED, size=18),
                                        ft.Text("Scan Food", weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                on_click=on_scan_click,
                                style=ft.ButtonStyle(
                                    bgcolor="#FFFFFF",
                                    color=ThemeColors.TEXT_PRIMARY,
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                ),
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    width=170 if (metrics["is_desktop"] or metrics["is_tablet"]) else 132,
                    height=160 if (metrics["is_desktop"] or metrics["is_tablet"]) else 120,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Stack(
                        controls=[
                            ft.Container(
                                left=40 if (metrics["is_desktop"] or metrics["is_tablet"]) else 36,
                                top=((160 - 138) // 2) if (metrics["is_desktop"] or metrics["is_tablet"]) else ((120 - 100) // 2),
                                width=92 if (metrics["is_desktop"] or metrics["is_tablet"]) else 70,
                                height=138 if (metrics["is_desktop"] or metrics["is_tablet"]) else 100,
                                border_radius=22,
                                bgcolor="#6FAF80",
                            ),
                            ft.Container(
                                left=0,
                                top=70 if (metrics["is_desktop"] or metrics["is_tablet"]) else 66,
                                width=56 if (metrics["is_desktop"] or metrics["is_tablet"]) else 44,
                                height=56 if (metrics["is_desktop"] or metrics["is_tablet"]) else 44,
                                border_radius=28,
                                bgcolor="#4E8F5C",
                            ),
                            ft.Container(
                                left=106 if (metrics["is_desktop"] or metrics["is_tablet"]) else 80,
                                top=76 if (metrics["is_desktop"] or metrics["is_tablet"]) else 68,
                                width=56 if (metrics["is_desktop"] or metrics["is_tablet"]) else 44,
                                height=56 if (metrics["is_desktop"] or metrics["is_tablet"]) else 44,
                                border_radius=28,
                                bgcolor="#3F7F4D",
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )

    top_card_height = 250 if (metrics["is_desktop"] or metrics["is_tablet"]) else None
    lower_card_height = 230 if (metrics["is_desktop"] or metrics["is_tablet"]) else None

    goal_tracker_card = ft.Container(
        expand=True,
        height=top_card_height,
        bgcolor="#FFFFFF",
        border_radius=16,
        padding=12,
        content=ft.Column(
            expand=True,
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Goal Tracker", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            bgcolor="#F6F7F9",
                            border_radius=8,
                            padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                            content=ft.Text("This Month", size=11, color=ThemeColors.TEXT_SECONDARY),
                        ),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        info_tile(
                            "Food Saved",
                            f"{food_saved_lbs:g} lbs",
                            "Estimated from your scans",
                            ft.Icons.MONITOR_WEIGHT_OUTLINED,
                        ),
                        info_tile(
                            "Pantry Stock",
                            str(pantry_item_count),
                            "Items you added",
                            ft.Icons.INVENTORY_2_OUTLINED,
                        ),
                        info_tile(
                            "Products Scanned",
                            str(scan_count),
                            "Successful lookups",
                            ft.Icons.QR_CODE_SCANNER,
                        ),
                    ],
                ),
            ],
        ),
    )

    recent_items = [item for item in list(recent_products or []) if isinstance(item, dict)][:5]

    if recent_items:
        recent_scanned_rows: list[ft.Control] = []
        for recent_product in recent_items:
            product_name = str(recent_product.get("product_name") or "Unknown product")
            recent_scanned_rows.append(
                ft.GestureDetector(
                    on_tap=(lambda _, product=recent_product: on_recent_product_click(product)) if on_recent_product_click else None,
                    content=ft.Container(
                        border_radius=10,
                        bgcolor="#F8FAFC",
                        padding=ft.Padding(left=8, top=6, right=8, bottom=6),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.Icons.QR_CODE_SCANNER, size=15, color=ThemeColors.GREEN_TEXT),
                                        ft.Text(
                                            product_name,
                                            size=12,
                                            color=ThemeColors.TEXT_PRIMARY,
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                ),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=15, color=ThemeColors.TEXT_INACTIVE),
                            ],
                        ),
                    ),
                )
            )
    else:
        recent_scanned_rows = [
            ft.Container(
                border_radius=10,
                bgcolor="#F8FAFC",
                padding=ft.Padding(left=8, top=10, right=8, bottom=10),
                content=ft.Text("No recent scans yet.", size=12, color=ThemeColors.TEXT_SECONDARY),
            )
        ]

    recent_activity_card = ft.Container(
        expand=True,
        height=top_card_height,
        bgcolor="#FFFFFF",
        border_radius=16,
        padding=12,
        content=ft.Column(
            expand=True,
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Recently Scanned", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{len(recent_items)} items", size=11, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
                ft.Column(expand=True, spacing=8, controls=recent_scanned_rows),
                ft.Container(
                    alignment=ft.Alignment(0, 0),
                    content=ft.Button(
                        "Open Scanner",
                        on_click=on_scan_click,
                        style=ft.ButtonStyle(
                            bgcolor="#FFFFFF",
                            color=ThemeColors.TEXT_PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    ),
                ),
            ],
        ),
    )

    top_row_cards: ft.Control
    lower_cards_block: ft.Control
    if metrics["is_desktop"] or metrics["is_tablet"]:
        top_row_cards = ft.Row(spacing=10, controls=[goal_tracker_card, recent_activity_card])
        lower_cards = ft.Row(
            expand=True,
            spacing=10,
            controls=[
                ft.Container(expand=True, height=lower_card_height, content=community_impact_card()),
                ft.Container(expand=True, height=lower_card_height, content=top_categories_card()),
                ft.Container(expand=True, height=lower_card_height, content=challenges_card()),
            ],
        )
        lower_cards_block = ft.Container(expand=True, content=lower_cards)
    else:
        top_row_cards = ft.Column(spacing=10, controls=[goal_tracker_card, recent_activity_card])
        lower_cards = ft.Column(spacing=10, controls=[community_impact_card(), top_categories_card(), challenges_card()])
        lower_cards_block = lower_cards

    scroll_content = ft.Column(
        expand=True,
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("PantryIQ Connect", size=44 if metrics["is_desktop"] else 34, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
                            ft.Text("Welcome back, Jamie!", size=20 if metrics["is_desktop"] else 16, weight=ft.FontWeight.W_600),
                            ft.Text(
                                "Here's what's happening with your pantry and community impact.",
                                size=12,
                                color=ThemeColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE, icon_color=ThemeColors.TEXT_TERTIARY),
                ],
            ),
            hero_banner,
            top_row_cards,
            lower_cards_block,
            ft.Container(height=74),
        ],
    )

    bottom_bar = ft.Container(
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
        padding=ft.Padding(left=content_padding, top=16, right=content_padding, bottom=0),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color=ThemeColors.SHELL_SHADOW,
            offset=ft.Offset(0, 8),
        ),
        content=ft.Stack(
            controls=[
                scroll_content,
                bottom_bar,
            ],
        ),
    )
