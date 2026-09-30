import unittest

from pages.ai_image_service import build_meal_fallback_image_url
from pages.meal_suggestion_service import _estimate_recipe_time, _fallback_suggestions, _food_role, _is_seasoning, _normalize_suggestion, rank_pantry_items


class MealSuggestionTests(unittest.TestCase):
    def setUp(self):
        self.inventory = rank_pantry_items([
            {"name": "Chicken breast", "shelf_life": "2 days", "risk": "High Risk"},
            {"name": "Baby spinach", "shelf_life": "1 day", "risk": "High Risk"},
            {"name": "Brown rice", "shelf_life": "3 months", "risk": "Low Risk"},
            {"name": "Greek yogurt", "shelf_life": "4 days", "risk": "Medium Risk"},
            {"name": "Apples", "shelf_life": "2 weeks", "risk": "Low Risk"},
        ])

    def test_fallback_meals_use_compatible_subsets_and_real_steps(self):
        suggestions = _fallback_suggestions(self.inventory, variation=1)

        self.assertEqual(6, len(suggestions))
        self.assertEqual(6, len({meal["title"] for meal in suggestions}))
        self.assertTrue(all(1 <= len(meal["pantry_items_used"]) <= 3 for meal in suggestions))
        self.assertTrue(all(len(meal["directions"]) >= 4 for meal in suggestions))
        self.assertFalse(any("Prepare and measure every ingredient" in step for meal in suggestions for step in meal["directions"]))
        roast = next(meal for meal in suggestions if meal["title"].endswith("Roast"))
        self.assertNotIn("Brown rice", roast["pantry_items_used"])
        self.assertNotIn("Baby spinach", roast["pantry_items_used"])

    def test_fallback_varies_titles_and_avoids_repeated_defaults(self):
        first_titles = [meal["title"] for meal in _fallback_suggestions(self.inventory, variation=1)]
        second_titles = [meal["title"] for meal in _fallback_suggestions(self.inventory, variation=2)]
        ingredient_names = [ingredient["name"].casefold() for meal in _fallback_suggestions(self.inventory) for ingredient in meal["ingredients"]]

        self.assertNotEqual(first_titles, second_titles)
        self.assertNotIn("black pepper", ingredient_names)
        self.assertLessEqual(ingredient_names.count("brown rice"), 2)

    def test_remote_meal_cannot_force_unselected_pantry_items(self):
        meal = _normalize_suggestion(
            {
                "title": "Chicken Skillet",
                "pantry_items_used": ["Chicken breast", "Baby spinach", "Brown rice", "Greek yogurt"],
                "ingredients": [
                    {"name": "Chicken breast", "amount": "1 pound"},
                    {"name": "Baby spinach", "amount": "2 cups"},
                    {"name": "Brown rice", "amount": "1 cup"},
                    {"name": "Greek yogurt", "amount": "1 cup"},
                ],
                "directions": ["Cook the chicken, then wilt in the spinach and serve over rice."],
            },
            self.inventory,
        )

        self.assertEqual(3, len(meal["pantry_items_used"]))
        self.assertNotIn("Greek yogurt", [ingredient["name"] for ingredient in meal["ingredients"]])

    def test_remote_meal_includes_every_declared_pantry_item_as_an_ingredient(self):
        meal = _normalize_suggestion(
            {
                "title": "Chicken and Spinach Skillet",
                "pantry_items_used": ["Chicken breast", "Baby spinach"],
                "ingredients": [
                    {"name": "Chicken breast", "amount": "1 pound"},
                    {"name": "Olive oil", "amount": "1 tablespoon"},
                ],
                "directions": ["Cook the chicken, then add the spinach."],
            },
            self.inventory,
        )

        ingredient_names = {ingredient["name"] for ingredient in meal["ingredients"]}
        self.assertEqual({"Chicken breast", "Baby spinach"}, set(meal["pantry_items_used"]))
        self.assertTrue(set(meal["pantry_items_used"]).issubset(ingredient_names))

    def test_fallback_directions_do_not_claim_missing_food_roles(self):
        vegetable_only_inventory = rank_pantry_items([
            {"name": "Baby spinach", "shelf_life": "1 day", "risk": "High Risk"},
            {"name": "Broccoli", "shelf_life": "3 days", "risk": "Medium Risk"},
        ])

        suggestions = _fallback_suggestions(vegetable_only_inventory)

        for meal in suggestions:
            directions = " ".join(meal["directions"]).casefold()
            self.assertNotIn("the protein", directions)
            self.assertNotIn("raw protein", directions)

    def test_main_dish_gets_missing_balance_ingredients(self):
        meal = _normalize_suggestion(
            {
                "title": "Creamy Rice Bowl",
                "meal_type": "main",
                "pantry_items_used": ["Brown rice"],
                "ingredients": [{"name": "Brown rice", "amount": "2 cups cooked"}],
                "directions": ["Warm the rice and serve."],
            },
            self.inventory,
        )

        ingredient_names = [ingredient["name"].casefold() for ingredient in meal["ingredients"]]
        self.assertEqual("main", meal["meal_type"])
        self.assertTrue(any("bean" in name or "lentil" in name or "chickpea" in name for name in ingredient_names))
        self.assertTrue(any("broccoli" in name or "spinach" in name or "vegetable" in name for name in ingredient_names))
        self.assertTrue(any("paprika" in name or "cumin" in name or "herb" in name for name in ingredient_names))

    def test_every_fallback_main_has_protein_vegetables_and_seasoning(self):
        for meal in _fallback_suggestions(self.inventory):
            ingredient_names = [str(ingredient["name"]) for ingredient in meal["ingredients"]]
            roles = {_food_role(name) for name in ingredient_names}

            self.assertEqual("main", meal["meal_type"])
            self.assertIn("protein", roles)
            self.assertIn("vegetable", roles)
            self.assertTrue(any(_is_seasoning(name) for name in ingredient_names))

    def test_dessert_and_appetizer_are_exempt_from_balance_additions(self):
        for meal_type, title in (("dessert", "Apple Crisp"), ("appetizer", "Apple Bites")):
            meal = _normalize_suggestion(
                {
                    "title": title,
                    "meal_type": meal_type,
                    "pantry_items_used": ["Apples"],
                    "ingredients": [
                        {"name": "Apples", "amount": "4"},
                        {"name": "Cinnamon", "amount": "1 teaspoon"},
                    ],
                    "directions": ["Prepare and serve."],
                },
                self.inventory,
            )

            self.assertEqual(meal_type, meal["meal_type"])
            self.assertEqual(["Apples", "Cinnamon"], [ingredient["name"] for ingredient in meal["ingredients"]])

    def test_recipe_time_is_estimated_from_directions(self):
        estimate = _estimate_recipe_time(
            "Slow Simmered Stew",
            [{"name": "Lentils"}, {"name": "Carrots"}, {"name": "Broth"}],
            ["Prepare the ingredients.", "Simmer for 40 to 50 minutes.", "Rest for 5 minutes."],
        )

        self.assertEqual("Estimated 55-65 minutes", estimate)

    def test_normalization_replaces_provided_generic_time_with_estimate(self):
        meal = _normalize_suggestion(
            {
                "title": "Chicken and Spinach Skillet",
                "meal_type": "main",
                "pantry_items_used": ["Chicken breast", "Baby spinach"],
                "ingredients": [
                    {"name": "Chicken breast", "amount": "1 pound"},
                    {"name": "Baby spinach", "amount": "2 cups"},
                    {"name": "Smoked paprika", "amount": "1 teaspoon"},
                ],
                "directions": ["Cook for 12 to 15 minutes.", "Rest for 5 minutes."],
                "prep_time": "About 30 minutes",
            },
            self.inventory,
        )

        self.assertEqual("Estimated 30 minutes", meal["prep_time"])
        self.assertNotEqual("About 30 minutes", meal["prep_time"])

    def test_fallback_times_vary_by_cooking_method(self):
        suggestions = _fallback_suggestions(self.inventory)
        estimates = {meal["title"].split()[-1]: meal["prep_time"] for meal in suggestions}

        self.assertNotEqual(estimates["Salad"], estimates["Roast"])
        self.assertTrue(all(value.startswith("Estimated ") for value in estimates.values()))

    def test_meal_photo_fallback_matches_the_dish_category(self):
        salad_url = build_meal_fallback_image_url("Garden Chickpea Salad")
        soup_url = build_meal_fallback_image_url("Lentil Carrot Soup")

        self.assertIn("photo-1546069901-ba9599a7e63c", salad_url)
        self.assertIn("photo-1547592166-23ac45744acd", soup_url)
        self.assertNotEqual(salad_url, soup_url)


if __name__ == "__main__":
    unittest.main()