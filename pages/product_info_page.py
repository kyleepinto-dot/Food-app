import flet as ft
from typing import cast

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
        border_radius=ThemeColors.CARD_RADIUS_INNER,
        bgcolor=ThemeColors.ACCENT_YELLOW_SUBTLE,
        padding=ThemeColors.CARD_PADDING,
        content=ft.Row(
            spacing=10,
            controls=[
                icon_control,
                ft.Column(
                    expand=True,
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


def _derive_product_handling_tips(product: dict) -> dict:
    """Build product-specific handling tips from Open Food Facts metadata."""

    text = " ".join(
        [
            str(product.get("product_name") or "").lower(),
            str(product.get("generic_name") or "").lower(),
            str(product.get("categories") or "").lower(),
            str(product.get("ingredients_text") or "").lower(),
        ]
    )

    ethylene_producers = {
        "apple",
        "apples",
        "banana",
        "bananas",
        "avocado",
        "avocados",
        "tomato",
        "tomatoes",
        "pear",
        "pears",
        "peach",
        "peaches",
        "mango",
        "mangoes",
        "kiwi",
        "kale",
        "melon",
        "melons",
        "plum",
        "plums",
    }
    ethylene_sensitive = {
        "lettuce",
        "spinach",
        "broccoli",
        "cucumber",
        "cucumbers",
        "carrot",
        "carrots",
        "potato",
        "potatoes",
        "onion",
        "onions",
        "cauliflower",
        "green beans",
        "herbs",
    }

    producer_match = any(word in text for word in ethylene_producers)
    sensitive_match = any(word in text for word in ethylene_sensitive)
    produce_match = any(word in text for word in ["fruit", "vegetable", "produce", "salad"]) or producer_match or sensitive_match

    ethylene_needed = producer_match or sensitive_match or produce_match

    if producer_match and sensitive_match:
        ethylene_tip = (
            "This product appears to include mixed produce. Keep it in a ventilated drawer and "
            "separate high-ethylene items from leafy or sensitive vegetables."
        )
    elif producer_match:
        ethylene_tip = (
            "This product appears ethylene-producing. Store away from ethylene-sensitive produce "
            "such as leafy greens, cucumbers, and broccoli."
        )
    elif sensitive_match:
        ethylene_tip = (
            "This product appears ethylene-sensitive. Keep it away from apples, bananas, avocados, "
            "and tomatoes to slow spoilage."
        )
    else:
        ethylene_tip = "Ethylene separation is usually not critical for this product; prioritize proper temperature storage."

    # Waste guidance is selected by product type so users get actionable advice
    # that matches how this food is typically stored and consumed.
    if any(word in text for word in ["milk", "yogurt", "cream", "cheese", "dairy"]):
        waste_tip = (
            "Refrigerate promptly, keep sealed, and mark the open date; use opened portions first in cooking or smoothies before opening a new pack."
        )
    elif any(word in text for word in ["fish", "chicken", "meat", "beef", "pork", "turkey"]):
        waste_tip = (
            "Divide into meal-size portions on day one and freeze extras immediately; thaw only what you plan to cook within 24 hours."
        )
    elif any(word in text for word in ["frozen", "ice cream", "frozen food", "ready meal"]):
        waste_tip = (
            "Keep frozen items grouped, avoid repeated thaw-refreeze cycles, and finish opened packs soon to prevent texture and flavor loss."
        )
    elif any(word in text for word in ["bread", "bakery", "bagel", "bun", "pastry"]):
        waste_tip = (
            "Freeze part of the pack early and keep only 1-2 days at room temperature; toast or reheat portions as needed."
        )
    elif any(word in text for word in ["snack", "chips", "crackers", "cookies", "cereal", "granola"]):
        waste_tip = (
            "Reseal tightly after each use, transfer to an airtight container if needed, and buy pack sizes that match your weekly use."
        )
    elif any(word in text for word in ["sauce", "condiment", "spread", "jam", "pickle", "dressing"]):
        waste_tip = (
            "Use clean utensils to avoid contamination, refrigerate after opening when required, and place near eye-level so it gets used regularly."
        )
    elif produce_match:
        waste_tip = (
            "Sort and use the ripest pieces first, keep produce dry before storage, and prep or freeze extras before quality drops."
        )
    else:
        waste_tip = (
            "Label with opened date, keep oldest items at the front, and plan one meal each week specifically to use near-expiry products."
        )

    return {
        "ethylene_tip": ethylene_tip,
        "ethylene_needed": ethylene_needed,
        "waste_tip": waste_tip,
    }


def _fattom_grid(metrics: dict) -> ft.Container:
    cells = [
        ("Food", "Medium", "🍽️"),
        ("Acidity", "Medium", "🧪"),
        ("Time", "Medium", "⏱️"),
        ("Temperature", "Medium", "🌡️"),
        ("Oxygen", "Low", "💨"),
        ("Moisture", "High", "💧"),
    ]

    cards_per_row = 3 if metrics["is_desktop"] else 2
    shell_inner_width = int(metrics["shell_width"] - 32)
    available = shell_inner_width - (ThemeColors.CARD_PADDING * 2) - (8 * (cards_per_row - 1))
    card_width = max(118, int(available / cards_per_row))

    def card(title: str, value: str, icon: str) -> ft.Container:
        return ft.Container(
            width=card_width,
            border_radius=ThemeColors.CARD_RADIUS_INNER,
            bgcolor=ThemeColors.ACCENT_YELLOW_SUBTLE,
            padding=ThemeColors.CARD_PADDING,
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
        border_radius=ThemeColors.CARD_RADIUS_INNER,
        bgcolor=ThemeColors.GREEN_SURFACE_SOFT,
        padding=ThemeColors.CARD_PADDING,
        content=ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                card(cells[0][0], cells[0][1], cells[0][2]),
                card(cells[1][0], cells[1][1], cells[1][2]),
                card(cells[2][0], cells[2][1], cells[2][2]),
                card(cells[3][0], cells[3][1], cells[3][2]),
                card(cells[4][0], cells[4][1], cells[4][2]),
                card(cells[5][0], cells[5][1], cells[5][2]),
            ],
        ),
    )


def build_product_info_shell(metrics: dict, product: dict, on_back_to_scan_click) -> ft.Container:
    """Render food facts page using scanned food data on the same app view."""

    product_name = str(product.get("product_name") or "Unknown product")
    category_text = str(product.get("categories") or "Food item")
    profile = _derive_food_profile(product)
    handling_tips = _derive_product_handling_tips(product)

    summary_text = f"{product_name} is categorized as {category_text}. {profile['storage']}"

    image_sources: list[dict[str, str]] = []
    ai_image_url = product.get("ai_image_url")
    off_image_url = product.get("best_image_url")

    if isinstance(ai_image_url, str) and ai_image_url:
        image_sources.append({"label": "AI Image", "url": ai_image_url})
    if isinstance(off_image_url, str) and off_image_url:
        image_sources.append({"label": "Open Food Facts", "url": off_image_url})

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
    if image_sources:
        active_image = {"index": 0}
        gallery_image = ft.Image(src=image_sources[0]["url"], height=210)
        source_label = ft.Text(
            image_sources[0]["label"],
            size=11,
            color="#FFFFFF",
            weight=ft.FontWeight.BOLD,
        )

        indicator_dots: list[ft.Text] = [
            ft.Text("●" if i == 0 else "○", color="#FFFFFF", size=12) for i in range(len(image_sources))
        ]

        def set_active_image(next_index: int) -> None:
            active_image["index"] = next_index % len(image_sources)
            current = image_sources[active_image["index"]]
            gallery_image.src = current["url"]
            source_label.value = current["label"]
            for i, dot in enumerate(indicator_dots):
                dot.value = "●" if i == active_image["index"] else "○"

            if gallery_image.page is not None:
                gallery_image.update()
                source_label.update()
                for dot in indicator_dots:
                    dot.update()

        def show_previous(_):
            set_active_image(active_image["index"] - 1)

        def show_next(_):
            set_active_image(active_image["index"] + 1)

        def on_swipe_end(e):
            primary_velocity = getattr(e, "primary_velocity", 0) or 0
            if len(image_sources) < 2:
                return
            if primary_velocity < -20:
                show_next(None)
            elif primary_velocity > 20:
                show_previous(None)

        side_arrow_style = {
            "width": 40,
            "height": 40,
            "border_radius": 20,
            "bgcolor": "#80343A40",
            "alignment": ft.Alignment(0, 0),
        }

        arrow_controls: list[ft.Control] = []
        if len(image_sources) > 1:
            arrow_controls = [
                ft.Container(
                    left=10,
                    top=85,
                    content=ft.GestureDetector(
                        on_tap=show_previous,
                        content=ft.Container(
                            width=side_arrow_style["width"],
                            height=side_arrow_style["height"],
                            border_radius=side_arrow_style["border_radius"],
                            bgcolor=side_arrow_style["bgcolor"],
                            alignment=side_arrow_style["alignment"],
                            content=ft.Icon(ft.Icons.CHEVRON_LEFT, color="#F2F2F2", size=20),
                        ),
                    ),
                ),
                ft.Container(
                    right=10,
                    top=85,
                    content=ft.GestureDetector(
                        on_tap=show_next,
                        content=ft.Container(
                            width=side_arrow_style["width"],
                            height=side_arrow_style["height"],
                            border_radius=side_arrow_style["border_radius"],
                            bgcolor=side_arrow_style["bgcolor"],
                            alignment=side_arrow_style["alignment"],
                            content=ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#F2F2F2", size=20),
                        ),
                    ),
                ),
            ]

        image_control = ft.Column(
            spacing=6,
            controls=cast(list[ft.Control], [
                ft.GestureDetector(
                    on_horizontal_drag_end=on_swipe_end,
                    content=ft.Container(
                        expand=True,
                        content=ft.Stack(
                            controls=cast(
                                list[ft.Control],
                                [
                                    ft.Container(expand=True, alignment=ft.Alignment(0, 0), content=gallery_image),
                                ] + arrow_controls,
                            ),
                        ),
                    ),
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=cast(list[ft.Control], [
                        ft.Column(
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=cast(list[ft.Control], [
                                source_label,
                                ft.Row(spacing=4, controls=cast(list[ft.Control], indicator_dots)),
                            ]),
                        ),
                    ]),
                ),
            ]),
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

    storage_cards: ft.Control
    if metrics["is_desktop"] or metrics["is_tablet"]:
        storage_cards = ft.Row(
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
        )
    else:
        storage_cards = ft.Column(
            spacing=10,
            controls=[
                _line("Storage Recommendation", profile["storage"], "🧊"),
                _line("Shelf Life", profile["shelf_life"], "📅"),
            ],
        )

    details_controls: list[ft.Control] = [
        ft.Text("Summary", size=13, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
        _line("Summary", summary_text, "🧾"),
        storage_cards,
        _line("Immediate Actions", "Keep in a cool place and use oldest stock first.", "✅"),
        _line("Warnings", "Discard if strong odor, mold, or unusual texture appears.", "⚠️"),
        ft.Text("FATTOM Dashboard", size=13, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
        _fattom_grid(metrics),
        _line("Waste Reduction Tips", handling_tips["waste_tip"], "♻️"),
    ]

    if bool(handling_tips.get("ethylene_needed")):
        details_controls.append(_line("Ethylene Compatibility", handling_tips["ethylene_tip"], "🍎"))

    content_controls: list[ft.Control] = [
        ft.Container(
            bgcolor=ThemeColors.GREEN_SURFACE_SOFT,
            border_radius=24,
            padding=ft.Padding(
                left=ThemeColors.CARD_PADDING,
                top=ThemeColors.CARD_PADDING,
                right=ThemeColors.CARD_PADDING,
                bottom=ThemeColors.CARD_PADDING,
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=header_controls,
            ),
        ),
        ft.Container(
            padding=ft.Padding(left=16, top=ThemeColors.CARD_PADDING, right=16, bottom=ThemeColors.CARD_PADDING),
            content=ft.Column(
                spacing=ThemeColors.SECTION_SPACING,
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
        # Reserve space so the floating pantry button does not hide final cards
        # while users scroll the product details.
        ft.Container(height=84),
    ]

    floating_add_button = ft.Container(
        left=16,
        right=16,
        bottom=8,
        content=ft.Button(
            content=ft.Text("Add Product To Pantry"),
            on_click=lambda _: None,
            style=ft.ButtonStyle(
                bgcolor=ThemeColors.ACCENT_YELLOW,
                color=ThemeColors.TEXT_PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=18),
                shadow_color="#33000000",
            ),
        ),
    )

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
        content=ft.Stack(
            controls=[
                ft.Column(
                    spacing=ThemeColors.SECTION_SPACING,
                    scroll=ft.ScrollMode.AUTO,
                    controls=content_controls,
                ),
                floating_add_button,
            ],
        ),
    )
