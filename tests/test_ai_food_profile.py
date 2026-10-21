import json
import unittest

import flet as ft

from pages.ai_food_profile_service import _build_local_profile, _parse_profile_response
from pages.product_info_page import _product_title_size, build_product_info_shell
from pages.theme import ThemeColors


def _text_values(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text):
        values.append(str(control.value or ""))

    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        values.extend(_text_values(content))

    controls = getattr(control, "controls", None)
    if isinstance(controls, list):
        for child in controls:
            if isinstance(child, ft.Control):
                values.extend(_text_values(child))
    return values


def _controls_of_type(control: ft.Control, control_type: type[ft.Control]) -> list[ft.Control]:
    matches: list[ft.Control] = []
    if isinstance(control, control_type):
        matches.append(control)

    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        matches.extend(_controls_of_type(content, control_type))

    controls = getattr(control, "controls", None)
    if isinstance(controls, list):
        for child in controls:
            if isinstance(child, ft.Control):
                matches.extend(_controls_of_type(child, control_type))
    return matches


class AiFoodProfileTests(unittest.TestCase):
    def test_product_title_size_reduces_for_long_mobile_names(self):
        metrics = {
            "is_desktop": False,
            "is_tablet": False,
            "shell_width": 390,
            "shell_height": 760,
        }

        self.assertEqual(_product_title_size("Greek Yogurt", metrics), 26)
        self.assertEqual(_product_title_size("Extra long family size strawberry yogurt package", metrics), 22)
        self.assertEqual(_product_title_size("A" * 80, metrics), 18)

    def test_parser_rejects_ambiguous_shelf_life_and_storage(self):
        payload = {
            "risk": "Medium Risk",
            "confidence": "High Confidence",
            "shelf_life": "3-7 days",
            "storage": "Keep refrigerated.",
            "immediate_actions": "Use soon.",
            "warnings": "Discard if spoiled.",
            "fattom": {},
        }

        self.assertIsNone(_parse_profile_response(json.dumps(payload)))

    def test_parser_accepts_explicit_package_state_guidance(self):
        payload = {
            "risk": "Medium Risk",
            "confidence": "High Confidence",
            "shelf_life": "Unopened: follow package date. After opening: use within 3-7 days.",
            "storage": "Before opening: keep cool. After opening: refrigerate and reseal.",
            "immediate_actions": "If unopened, check the date. After opening, mark the open date.",
            "warnings": "Discard if spoiled.",
            "fattom": {},
        }

        parsed = _parse_profile_response(json.dumps(payload))

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertIn("After opening", parsed["shelf_life"])
        self.assertIn("After opening", parsed["storage"])

    def test_local_profiles_always_identify_package_state(self):
        examples = [
            ("Greek yogurt", "Dairy"),
            ("Chicken breast", "Meat"),
            ("Frozen peas", "Frozen foods"),
            ("Bread", "Bakery"),
            ("Brown rice", "Dry grains"),
            ("Apples", "Fresh produce"),
            ("Unknown item", "Packaged food"),
        ]

        for name, category in examples:
            with self.subTest(name=name):
                profile = _build_local_profile(name, category)
                combined = f"{profile['shelf_life']} {profile['storage']}".casefold()
                self.assertTrue(
                    any(
                        marker in combined
                        for marker in ("unopened", "before opening", "after opening", "opening not applicable")
                    )
                )

    def test_waste_reduction_is_immediately_before_fattom(self):
        product = {
            "product_name": "Apples",
            "categories": "Fresh produce",
            "ai_food_profile": _build_local_profile("Apples", "Fresh produce"),
            "ai_food_profile_status": "ready_local",
        }
        shell = build_product_info_shell(
            metrics={
                "is_desktop": False,
                "is_tablet": False,
                "shell_width": 390,
                "shell_height": 760,
            },
            product=product,
            on_back_to_scan_click=lambda _: None,
            on_home_click=lambda _: None,
            on_scan_click=lambda _: None,
            on_pantry_click=lambda _: None,
            on_me_click=lambda _: None,
            on_add_to_pantry=lambda *_: None,
        )

        text_values = _text_values(shell)
        waste_index = text_values.index("Waste Reduction Tips")
        fattom_index = text_values.index("FATTOM Dashboard")
        ethylene_index = text_values.index("Ethylene Compatibility")

        self.assertLess(waste_index, fattom_index)
        self.assertLess(fattom_index, ethylene_index)

        quantity_fields = [
            control
            for control in _controls_of_type(shell, ft.TextField)
            if isinstance(control, ft.TextField) and control.label == "Quantity to add"
        ]
        self.assertEqual(len(quantity_fields), 1)
        self.assertEqual(quantity_fields[0].bgcolor, ThemeColors.INPUT_BACKGROUND)
