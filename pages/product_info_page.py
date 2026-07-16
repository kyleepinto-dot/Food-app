import flet as ft

from pages.theme import ThemeColors


def _line(label: str, value: str, icon: str | None = None) -> ft.Container:
    icon_control: ft.Control
    if icon:
        icon_control = ft.Container(
            width=28,
            height=28,
            border_radius=14,
            bgcolor=ThemeColors.ACCENT_YELLOW_SOFT,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(icon, size=16),
        )
    else:
        icon_control = ft.Container(width=0)

    return ft.Container(
        border_radius=14,
        bgcolor=ThemeColors.ACCENT_YELLOW_SUBTLE,
        padding=10,
        content=ft.Row(
            spacing=10,
            controls=[
                icon_control,
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(label, size=12, color=ThemeColors.GREEN_TEXT, weight=ft.FontWeight.W_600),
                        ft.Text(value if value else "Not available", size=14, color=ThemeColors.TEXT_PRIMARY),
                    ],
                ),
            ],
        ),
    )


def _derive_food_profile(product: dict) -> dict:
    text = " ".join(
        [
            str(product.get("product_name") or "").lower(),
            str(product.get("categories") or "").lower(),
            str(product.get("ingredients_text") or "").lower(),
        ]
    )

    if any(word in text for word in ["milk", "yogurt", "cream", "cheese", "fish", "chicken", "meat"]):
        risk = "High Risk"
        confidence = "High Confidence"
        shelf = "3-7 days"
        storage = "Store in refrigerator between 34-40F (1-4C)."
    elif any(word in text for word in ["potato", "onion", "garlic", "apple", "orange", "banana"]):
        risk = "Medium Risk"
        confidence = "High Confidence"
        shelf = "2-4 weeks"
        storage = "Store in a cool, dry place away from direct sunlight."
    else:
        risk = "Medium Risk"
        confidence = "Medium Confidence"
        shelf = "5-10 days"
        storage = "Store in a cool place and refrigerate after opening if needed."

    return {
        "risk": risk,
        "confidence": confidence,
        "shelf_life": shelf,
        "storage": storage,
    }


def _fattom_grid() -> ft.Container:
    cells = [
        ("Food", "Medium", "🍽️"),
        ("Acidity", "Medium", "🧪"),
        ("Time", "Medium", "⏱️"),
        ("Temperature", "Medium", "🌡️"),
        ("Oxygen", "Low", "💨"),
        ("Moisture", "High", "💧"),
    ]

    def card(title: str, value: str, icon: str) -> ft.Container:
        return ft.Container(
            expand=True,
            border_radius=12,
            bgcolor=ThemeColors.ACCENT_YELLOW_SUBTLE,
            padding=8,
            content=ft.Column(
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(title, size=11, color=ThemeColors.GREEN_TEXT, weight=ft.FontWeight.W_600),
                    ft.Text(icon, size=18),
                    ft.Text(value, size=11, color="#263040", weight=ft.FontWeight.BOLD),
                ],
            ),
        )

    return ft.Container(
        border_radius=14,
        bgcolor=ThemeColors.GREEN_SURFACE_SOFT,
        padding=10,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        card(cells[0][0], cells[0][1], cells[0][2]),
                        card(cells[1][0], cells[1][1], cells[1][2]),
                        card(cells[2][0], cells[2][1], cells[2][2]),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        card(cells[3][0], cells[3][1], cells[3][2]),
                        card(cells[4][0], cells[4][1], cells[4][2]),
                        card(cells[5][0], cells[5][1], cells[5][2]),
                    ],
                ),
            ],
        ),
    )


def build_product_info_shell(metrics: dict, product: dict, on_back_to_scan_click) -> ft.Container:
    """Render food facts page using scanned food data on the same app view."""

    product_name = str(product.get("product_name") or "Unknown product")
    category_text = str(product.get("categories") or "Food item")
    profile = _derive_food_profile(product)

    summary_text = f"{product_name} is categorized as {category_text}. {profile['storage']}"

    image_url = product.get("best_image_url")

    header_controls: list[ft.Control] = [
        ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, on_click=on_back_to_scan_click, icon_color="#0F0F0F"),
        ft.Text(
            "Product Details",
            size=34 if metrics["is_desktop"] else 24,
            weight=ft.FontWeight.BOLD,
            color=ThemeColors.GREEN_TEXT,
        ),
        ft.Container(width=40),
    ]

    image_control: ft.Control
    if image_url:
        image_control = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            content=ft.Image(
                src=str(image_url),
                height=210,
            ),
        )
    else:
        image_control = ft.Container(
            expand=True,
            height=210,
            alignment=ft.Alignment(0, 0),
            bgcolor=ThemeColors.GREEN_SURFACE_SOFT,
            content=ft.Text("No product image", color=ThemeColors.TEXT_INACTIVE),
        )

    hero = ft.Container(
        border_radius=20,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        height=240,
        content=ft.Stack(
            controls=[
                ft.Container(expand=True, alignment=ft.Alignment(0, 0), content=image_control),
                ft.Container(
                    left=0,
                    right=0,
                    bottom=0,
                    bgcolor="#88000000",
                    padding=ft.Padding(left=14, top=10, right=14, bottom=10),
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(product_name, size=36 if metrics["is_desktop"] else 30, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Container(
                                        border_radius=10,
                                        bgcolor=ThemeColors.ACCENT_YELLOW,
                                        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                                        content=ft.Text(profile["risk"], size=11, weight=ft.FontWeight.BOLD),
                                    ),
                                    ft.Container(
                                        border_radius=10,
                                        bgcolor=ThemeColors.GREEN_SURFACE_SOFT,
                                        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                                        content=ft.Text(profile["confidence"], size=11, weight=ft.FontWeight.BOLD),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )

    details_controls: list[ft.Control] = [
        ft.Text("Summary", size=13, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
        _line("Summary", summary_text, "🧾"),
        ft.Text("FATTOM Dashboard", size=13, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
        _fattom_grid(),
        ft.Row(
            spacing=10,
            controls=[
                ft.Container(
                    expand=True,
                    content=_line("Storage Recommendation", profile["storage"], "🧊"),
                ),
                ft.Container(
                    expand=True,
                    content=_line("Shelf Life", profile["shelf_life"], "📅"),
                ),
            ],
        ),
        _line("Immediate Actions", "Keep in a cool place and use oldest stock first.", "✅"),
        _line("Ethylene Compatibility", "Avoid storing next to apples and bananas.", "🍎"),
        _line("Waste Reduction Tips", "Use peels/stems in soups or stock where suitable.", "♻️"),
        _line("Warnings", "Discard if strong odor, mold, or unusual texture appears.", "⚠️"),
    ]

    content_controls: list[ft.Control] = [
        ft.Container(
            bgcolor=ThemeColors.GREEN_SURFACE_SOFT,
            border_radius=24,
            padding=ft.Padding(left=8, top=8, right=8, bottom=8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=header_controls,
            ),
        ),
        ft.Container(
            padding=ft.Padding(left=16, top=8, right=16, bottom=8),
            content=ft.Column(
                spacing=12,
                controls=[hero] + details_controls,
            ),
        ),
        ft.Container(
            padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            content=ft.Button(
                content=ft.Text("Scan Another Product"),
                on_click=on_back_to_scan_click,
                style=ft.ButtonStyle(
                    bgcolor=ThemeColors.BRAND_PRIMARY,
                    color=ThemeColors.BRAND_ON_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=16),
                ),
            ),
        ),
    ]

    return ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor=ThemeColors.GREEN_SURFACE,
        border_radius=34,
        padding=ft.Padding(left=0, top=0, right=0, bottom=16),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=30,
            color=ThemeColors.SHELL_SHADOW,
            offset=ft.Offset(0, 8),
        ),
        content=ft.Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            controls=content_controls,
        ),
    )
