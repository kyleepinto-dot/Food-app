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


def _pantry_item(name: str, qty: int, freshness: str, category: str, on_quantity_change, item_key: str) -> ft.Container:
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
                        ft.Text(f"Qty: {qty} | {category}", size=12, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    spacing=2,
                    controls=[
                        ft.Text(freshness, size=12, weight=ft.FontWeight.W_600, color=ThemeColors.GREEN_TEXT),
                        ft.Text("Added from product details", size=11, color=ThemeColors.TEXT_SECONDARY),
                        ft.Row(
                            tight=True,
                            spacing=2,
                            controls=[
                                ft.IconButton(
                                    ft.Icons.REMOVE,
                                    icon_size=16,
                                    icon_color=ThemeColors.GREEN_TEXT,
                                    tooltip="Decrease quantity",
                                    on_click=lambda _: on_quantity_change(item_key, -1),
                                ),
                                ft.Text(str(qty), size=14, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                                ft.IconButton(
                                    ft.Icons.ADD,
                                    icon_size=16,
                                    icon_color=ThemeColors.GREEN_TEXT,
                                    tooltip="Increase quantity",
                                    on_click=lambda _: on_quantity_change(item_key, 1),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )


def build_pantry_shell(
    metrics: dict,
    on_home_click,
    on_scan_click,
    on_me_click,
    on_meal_planner_click,
    on_dummy_meal_planner_click,
    pantry_products: list[dict],
    on_quantity_change,
) -> ft.Container:
    """Render pantry dashboard with the same style language as home/scan."""

    compact_nav = metrics["shell_width"] < 360
    pantry_items = [item for item in pantry_products if isinstance(item, dict)]
    pantry_item_count = sum(int(item.get("quantity") or 0) for item in pantry_items)

    if pantry_items:
        pantry_rows: list[ft.Control] = [
            _pantry_item(
                str(item.get("name") or "Unknown product"),
                int(item.get("quantity") or 1),
                str(item.get("freshness") or "Added"),
                str(item.get("category") or "Food item"),
                on_quantity_change,
                str(item.get("key") or ""),
            )
            for item in pantry_items
        ]
    else:
        pantry_rows = [
            ft.Container(
                bgcolor="#F7FAFC",
                border_radius=14,
                padding=12,
                content=ft.Text(
                    "No items in your pantry yet. Add a scanned product from Product Details.",
                    size=13,
                    color=ThemeColors.TEXT_SECONDARY,
                ),
            )
        ]

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
                        content=ft.Text(f"{pantry_item_count} Items", size=14, weight=ft.FontWeight.BOLD),
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
                    ft.Text("Pantry Items", size=16, weight=ft.FontWeight.BOLD, color=ThemeColors.TEXT_PRIMARY),
                ] + pantry_rows,
            ),
        ),
        ft.Row(
            spacing=8,
            controls=[
                ft.Button(
                    expand=True,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.RESTAURANT_MENU, color=ThemeColors.BRAND_ON_PRIMARY, size=18),
                            ft.Text("Meal Planner", weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    on_click=on_meal_planner_click,
                    style=ft.ButtonStyle(
                        bgcolor=ThemeColors.BRAND_PRIMARY,
                        color=ThemeColors.BRAND_ON_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=14),
                    ),
                ),
                ft.Button(
                    expand=True,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.SCIENCE_OUTLINED, color=ThemeColors.GREEN_TEXT, size=18),
                            ft.Text("Dummy Planner", weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    on_click=on_dummy_meal_planner_click,
                    style=ft.ButtonStyle(
                        bgcolor="#FFFFFF",
                        color=ThemeColors.GREEN_TEXT,
                        side=ft.BorderSide(width=1, color=ThemeColors.BRAND_PRIMARY),
                        shape=ft.RoundedRectangleBorder(radius=14),
                    ),
                ),
            ],
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
                                        ft.Text("0 items", size=18, weight=ft.FontWeight.BOLD),
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
                                        ft.Text(f"{pantry_item_count} items", size=18, weight=ft.FontWeight.BOLD),
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
                                        ft.Text("0 items", size=18, weight=ft.FontWeight.BOLD),
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
