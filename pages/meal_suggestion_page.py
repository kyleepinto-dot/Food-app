"""Meal Suggestion Planner screen."""

import flet as ft

from pages.pantry_page import build_nav_item
from pages.theme import ThemeColors


def _priority_card(item: dict, position: int) -> ft.Container:
    return ft.Container(
        bgcolor="#F7FAFC",
        border_radius=12,
        padding=10,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Container(
                    width=26,
                    height=26,
                    border_radius=13,
                    bgcolor=ThemeColors.BRAND_PRIMARY,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(str(position), size=12, weight=ft.FontWeight.BOLD, color=ThemeColors.BRAND_ON_PRIMARY),
                ),
                ft.Column(
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(str(item.get("name") or "Food item"), size=13, weight=ft.FontWeight.BOLD),
                        ft.Text(str(item.get("risk") or "Medium Risk"), size=11, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
                ft.Text(
                    str(item.get("expiry_label") or "Use soon"),
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=ThemeColors.GREEN_TEXT,
                ),
            ],
        ),
    )


def _meal_detail_content(suggestion: dict, image_url: str) -> list[ft.Control]:
    pantry_items = [str(value) for value in suggestion.get("pantry_items_used") or []]
    ingredients = [value for value in suggestion.get("ingredients") or [] if isinstance(value, dict)]
    directions = [str(value) for value in suggestion.get("directions") or []]
    controls: list[ft.Control] = []

    if image_url:
        controls.append(
            ft.Container(
                height=190,
                border_radius=16,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Image(src=image_url, fit=ft.BoxFit.COVER, width=1024, height=190),
            )
        )
    else:
        controls.append(
            ft.Container(
                height=120,
                border_radius=16,
                bgcolor=ThemeColors.PREVIEW_FALLBACK_BACKGROUND,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.IMAGE_OUTLINED, color=ThemeColors.GREEN_TEXT, size=30),
                        ft.Text("Creating an AI meal photo...", size=12, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
            )
        )

    controls.extend(
        [
            ft.Text(str(suggestion.get("title") or "Healthy Pantry Meal"), size=22, weight=ft.FontWeight.BOLD),
            ft.Text(str(suggestion.get("description") or ""), size=13, color=ThemeColors.TEXT_SECONDARY),
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.SCHEDULE, size=16, color=ThemeColors.GREEN_TEXT),
                    ft.Text(str(suggestion.get("prep_time") or "About 30 minutes"), size=12, weight=ft.FontWeight.W_600),
                ],
            ),
            ft.Divider(height=1, color=ThemeColors.DIVIDER),
            ft.Text("Uses from your pantry", size=15, weight=ft.FontWeight.BOLD),
            ft.Text(" • ".join(pantry_items), size=13, color=ThemeColors.GREEN_TEXT),
            ft.Text("All ingredients — 4 servings", size=17, weight=ft.FontWeight.BOLD),
        ]
    )
    controls.extend(
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=10,
            padding=8,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(str(ingredient.get("name") or "Ingredient"), size=13, weight=ft.FontWeight.W_600, expand=True),
                    ft.Text(str(ingredient.get("amount") or "As needed"), size=13, color=ThemeColors.GREEN_TEXT),
                ],
            ),
        )
        for ingredient in ingredients
    )
    controls.append(ft.Text("Directions", size=17, weight=ft.FontWeight.BOLD))
    controls.extend(
        ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=26,
                    height=26,
                    border_radius=13,
                    bgcolor=ThemeColors.BRAND_PRIMARY,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(str(index), size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ),
                ft.Text(step, size=13, color=ThemeColors.TEXT_SECONDARY, expand=True),
            ],
        )
        for index, step in enumerate(directions, start=1)
    )
    controls.extend(
        [
            ft.Container(
                bgcolor="#E8F5ED",
                border_radius=12,
                padding=10,
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text("Nutrition focus", size=13, weight=ft.FontWeight.BOLD, color=ThemeColors.GREEN_TEXT),
                        ft.Text(str(suggestion.get("nutrition_notes") or ""), size=12, color=ThemeColors.TEXT_SECONDARY),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=ThemeColors.ACCENT_YELLOW_SUBTLE,
                border_radius=12,
                padding=10,
                content=ft.Text(
                    str(suggestion.get("food_safety_note") or "Inspect food before use and follow safe cooking guidance."),
                    size=11,
                    color=ThemeColors.TRACKER_TEXT,
                ),
            ),
        ]
    )
    return controls


def build_meal_suggestion_shell(
    metrics: dict,
    on_back_click,
    on_home_click,
    on_scan_click,
    on_pantry_click,
    on_me_click,
    ranked_items: list[dict],
    meal_state: dict,
    on_meal_click,
    on_back_to_list_click,
    on_refresh_click,
) -> ft.Container:
    """Render the use-it-first AI meal planner and its loading states."""

    compact_nav = metrics["shell_width"] < 360
    status = str(meal_state.get("status") or "idle")
    suggestions = [item for item in meal_state.get("suggestions") or [] if isinstance(item, dict)]
    image_urls = [str(value or "") for value in meal_state.get("image_urls") or []]
    selected_value = meal_state.get("selected_index")
    selected_index = selected_value if isinstance(selected_value, int) and 0 <= selected_value < len(suggestions) else None

    if not ranked_items:
        planner_controls: list[ft.Control] = [
            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=42, color=ThemeColors.GREEN_TEXT),
            ft.Text("Your pantry is empty", size=19, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Add at least one food item before asking AI to plan a meal.",
                text_align=ft.TextAlign.CENTER,
                size=13,
                color=ThemeColors.TEXT_SECONDARY,
            ),
            ft.Button(
                "Go to Pantry",
                on_click=on_pantry_click,
                style=ft.ButtonStyle(bgcolor=ThemeColors.BRAND_PRIMARY, color=ThemeColors.BRAND_ON_PRIMARY),
            ),
        ]
    elif status in {"idle", "loading"} or not suggestions:
        planner_controls = [
            ft.ProgressRing(color=ThemeColors.BRAND_PRIMARY),
            ft.Text("Planning a healthy meal...", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(
                "AI is prioritizing the pantry items estimated to expire first.",
                text_align=ft.TextAlign.CENTER,
                size=13,
                color=ThemeColors.TEXT_SECONDARY,
            ),
        ]
    else:
        if selected_index is not None:
            selected_suggestion = suggestions[selected_index]
            image_url = image_urls[selected_index] if selected_index < len(image_urls) else ""
            planner_controls = _meal_detail_content(selected_suggestion, image_url)
        else:
            planner_controls = [
                ft.Text(
                    f"Choose from {len(suggestions)} healthy meal ideas",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ThemeColors.GREEN_TEXT,
                ),
                ft.Text(
                    "Select a dish to see every ingredient, exact amounts, and complete directions.",
                    size=12,
                    color=ThemeColors.TEXT_SECONDARY,
                ),
            ]
            for index, suggestion in enumerate(suggestions):
                pantry_items = [str(value) for value in suggestion.get("pantry_items_used") or []]
                thumbnail_url = image_urls[index] if index < len(image_urls) else ""
                thumbnail = (
                    ft.Image(src=thumbnail_url, width=64, height=64, fit=ft.BoxFit.COVER)
                    if thumbnail_url
                    else ft.Container(
                        width=64,
                        height=64,
                        bgcolor=ThemeColors.PREVIEW_FALLBACK_BACKGROUND,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.RESTAURANT, size=26, color=ThemeColors.GREEN_TEXT),
                    )
                )
                planner_controls.append(
                    ft.GestureDetector(
                        on_tap=lambda _, meal_index=index: on_meal_click(meal_index),
                        content=ft.Container(
                            bgcolor="#F9FBFA",
                            border=ft.Border.all(1, ThemeColors.DIVIDER),
                            border_radius=16,
                            padding=12,
                            content=ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(
                                        width=64,
                                        height=64,
                                        border_radius=12,
                                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                        content=thumbnail,
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=5,
                                        controls=[
                                            ft.Text(
                                                str(suggestion.get("title") or "Healthy Pantry Meal"),
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                f"Uses from pantry: {' • '.join(pantry_items)}",
                                                size=12,
                                                color=ThemeColors.GREEN_TEXT,
                                            ),
                                        ],
                                    ),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ThemeColors.GREEN_TEXT),
                                ],
                            ),
                        ),
                    )
                )
            planner_controls.append(
                ft.Button(
                    "Suggest More Meals",
                    on_click=on_refresh_click,
                    style=ft.ButtonStyle(
                        bgcolor=ThemeColors.BRAND_PRIMARY,
                        color=ThemeColors.BRAND_ON_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=14),
                    ),
                )
            )

    priority_rows = [_priority_card(item, index) for index, item in enumerate(ranked_items, start=1)]
    content_controls: list[ft.Control] = [
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=26,
            padding=ft.Padding(left=8, top=8, right=12, bottom=8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK_IOS_NEW,
                        on_click=on_back_to_list_click if selected_index is not None else on_back_click,
                        icon_color="#0F0F0F",
                    ),
                    ft.Text(
                        "Recipe Details" if selected_index is not None else "Meal Suggestion Planner",
                        size=20 if metrics["is_desktop"] else 17,
                        weight=ft.FontWeight.BOLD,
                        color=ThemeColors.GREEN_TEXT,
                    ),
                    ft.Container(width=36),
                ],
            ),
        ),
        ft.Container(
            bgcolor="#DFEBDD",
            border_radius=18,
            padding=14,
            content=ft.Column(
                spacing=7,
                controls=[
                    ft.Text("Expiring first to last", size=17, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Foods are sorted from the item to use soonest to the item that lasts longest.",
                        size=12,
                        color=ThemeColors.TEXT_SECONDARY,
                    ),
                ] + priority_rows,
            ),
        ) if ranked_items and selected_index is None else ft.Container(),
        ft.Container(
            bgcolor="#FFFFFF",
            border_radius=16,
            padding=14,
            content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER if status in {"idle", "loading"} else ft.CrossAxisAlignment.START,
                controls=planner_controls,
            ),
        ),
        ft.Container(height=74),
    ]

    bottom_nav_controls: list[ft.Control] = [
        ft.GestureDetector(on_tap=on_home_click, content=build_nav_item(ft.Icons.HOME_ROUNDED, "Dashboard", compact=compact_nav)),
        ft.GestureDetector(on_tap=on_scan_click, content=build_nav_item(ft.Icons.CAMERA_ALT_OUTLINED, "Scan Food", compact=compact_nav)),
        ft.GestureDetector(
            on_tap=on_pantry_click,
            content=build_nav_item(ft.Icons.INVENTORY_2_OUTLINED, "Pantry", selected=True, compact=compact_nav),
        ),
        ft.GestureDetector(on_tap=on_me_click, content=build_nav_item(ft.Icons.PERSON_OUTLINE, "Me", compact=compact_nav)),
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
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=bottom_nav_controls),
            ],
        ),
    )

    return ft.Container(
        width=metrics["shell_width"],
        height=metrics["shell_height"],
        bgcolor=ThemeColors.GREEN_SURFACE,
        border_radius=34,
        padding=ft.Padding(left=14, top=16, right=14, bottom=0),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=30, color=ThemeColors.SHELL_SHADOW, offset=ft.Offset(0, 8)),
        content=ft.Stack(
            controls=[
                ft.Column(spacing=ThemeColors.SECTION_SPACING, scroll=ft.ScrollMode.AUTO, controls=content_controls),
                bottom_nav_bar,
            ]
        ),
    )
