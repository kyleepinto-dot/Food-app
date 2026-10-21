"""
test_food_safety.py  —  automated tests for the food-safety rules in db.py.

WHAT IS A TEST?
    A test is a tiny program that runs YOUR code and then checks "is the answer
    what it should be?" using an assert. If the answer is right, the test PASSES.
    If your code ever changes in a way that breaks the rule, the test FAILS and
    tells you exactly which rule broke — before your users ever see it.

WHY IT MATTERS HERE:
    The food-safety rules are the promise of the whole app: homemade food never
    reaches strangers, and only sealed in-date food can be donated. These tests
    are a burglar alarm on those promises. If someone (even future-you) edits
    db.py and weakens a rule by accident, running these tests catches it.

HOW TO RUN (from the project folder, with the myenv Python):
    & "C:\\Users\\neesh\\Desktop\\myenv\\Scripts\\python.exe" tests\\test_food_safety.py
Read the output bottom-up: "OK" = all rules held; "FAILED" lists any that broke.

Each test builds its OWN brand-new empty database in a temp folder, so these
tests NEVER touch your real pantry.db.
"""

import os
import sys
import sqlite3
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import cv2
import numpy as np

# Let Python find db.py / queries.py, which live one folder up from tests/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db     # noqa: E402
from pages.product_cache import (
    AI_PROFILE_GUIDANCE_VERSION,
    load_ai_profile,
    load_product,
    prepare_image_for_cache,
    store_ai_profile,
    store_product,
)
from pages.ai_food_profile_service import get_ai_food_profile_service_signature
from pages.pantry_page import (
    DEFAULT_BEST_BY_DAYS,
    _suggested_best_by,
    scanned_product_draft,
)


class FoodSafetyTests(unittest.TestCase):

    def setUp(self):
        # A fresh, empty database for every single test.
        self.tmp = tempfile.mkdtemp()
        db.DB_PATH = os.path.join(self.tmp, "test.db")
        db.init_db()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- small helper: add a pantry item and return its id ---
    def _add_item(self, owner, name, safety, days_to_best_by):
        best_by = date.today() + timedelta(days=days_to_best_by)
        db.save_item(name, best_by, 1, "items", "Shelf", "",
                     safety_class=safety, owner_id=owner)
        con = sqlite3.connect(db.DB_PATH)
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT id FROM pantry_items WHERE owner_id=? AND name=? "
            "ORDER BY id DESC LIMIT 1", (owner, name)).fetchone()
        con.close()
        return row["id"]

    # ------------------------------------------------------------------
    # RULE 1: a homemade/opened share is HIDDEN from someone outside the Circle
    # ------------------------------------------------------------------
    def test_homemade_share_hidden_from_outsider(self):
        owner    = db.create_account("Owner", "owner@x.com", "pass1234")
        outsider = db.create_account("Outsider", "out@x.com", "pass1234")
        item = self._add_item(owner, "Leftover curry", "homemade_or_opened", 2)
        share_id = db.create_share(shared_by=owner, item_id=item,
                                   title="Leftover curry", safety_class="homemade_or_opened")

        # The outsider is NOT in the owner's Circle, so they must NOT see it.
        self.assertFalse(
            db.can_see_share(outsider, share_id),
            "Homemade share leaked to someone outside the Circle!")
        # Sanity: the owner can still see their own share.
        self.assertTrue(db.can_see_share(owner, share_id))

    def test_sealed_share_is_visible_to_the_community(self):
        owner    = db.create_account("Owner", "owner@x.com", "pass1234")
        outsider = db.create_account("Outsider", "out@x.com", "pass1234")
        item = self._add_item(owner, "Canned beans", "sealed_packaged", 200)
        share_id = db.create_share(shared_by=owner, item_id=item,
                                   title="Canned beans", safety_class="sealed_packaged")

        # Sealed food reaches the whole community, so an outsider CAN see it.
        self.assertTrue(
            db.can_see_share(outsider, share_id),
            "Sealed share should be visible to the community")

    # ------------------------------------------------------------------
    # RULE 2: only SEALED and IN-DATE items pass can_donate
    # ------------------------------------------------------------------
    def test_can_donate_accepts_only_sealed_in_date(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        past   = (date.today() - timedelta(days=1)).isoformat()

        self.assertTrue(db.can_donate("sealed_packaged", future),
                        "Sealed + in-date should be donatable")
        self.assertFalse(db.can_donate("homemade_or_opened", future),
                         "Homemade must NEVER be donatable")
        self.assertFalse(db.can_donate("fresh_produce", future),
                         "Produce is not donatable to a food bank")
        self.assertFalse(db.can_donate("sealed_packaged", past),
                         "Expired sealed must NOT be donatable")

    # ------------------------------------------------------------------
    # RULE 3: sharing from an item can NEVER make it less safe than the item
    # ------------------------------------------------------------------
    def test_share_cannot_widen_a_homemade_items_audience(self):
        owner = db.create_account("Owner", "owner@x.com", "pass1234")
        item = self._add_item(owner, "Leftover curry", "homemade_or_opened", 2)

        # Try to CHEAT: share the homemade item while claiming it is "sealed"
        # (which would reach a wider, less-safe audience).
        share_id = db.create_share(shared_by=owner, item_id=item,
                                   title="Leftover curry", safety_class="sealed_packaged")

        con = sqlite3.connect(db.DB_PATH)
        con.row_factory = sqlite3.Row
        stored = con.execute("SELECT safety_class FROM shares WHERE id=?",
                             (share_id,)).fetchone()["safety_class"]
        con.close()

        self.assertEqual(
            stored, "homemade_or_opened",
            "The share was allowed to be less safe than its pantry item!")

    def test_meal_plan_cache_requires_the_same_pantry_signature(self):
        owner = db.create_account("Planner", "planner@x.com", "pass1234")
        suggestions = [{
            "title": "Cached Lentil Soup",
            "ingredients": [{"name": "Lentils", "amount": "1 cup"}],
            "directions": ["Simmer until tender."],
        }]

        db.save_meal_plan_cache(owner, "pantry-signature-a", suggestions)
        db.save_meal_plan_image(owner, "pantry-signature-a", 0, b"image-bytes")

        cached = db.load_meal_plan_cache(owner, "pantry-signature-a")
        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertEqual(suggestions, cached["suggestions"])
        self.assertEqual([b"image-bytes"], cached["image_sources"])
        self.assertIsNone(db.load_meal_plan_cache(owner, "pantry-signature-b"))

    def test_product_scan_cache_persists_product_and_ai_profile(self):
        product = {
            "code": "0898999000022",
            "product_name": "Coconut Water",
            "categories": "Beverages",
            "best_image_url": "https://example.test/open-food-facts.jpg",
            "ai_image_url": "https://example.test/generated.jpg",
        }
        profile = {
            "risk": "Low Risk",
            "storage": "Refrigerate after opening.",
            "_provider": "remote",
        }

        store_product(product, "898999000022")
        store_ai_profile(product, profile)
        cache_key = str(product["_product_cache_key"])
        db.save_product_image_cache(cache_key, "open_food_facts", b"off-image", "image/jpeg")
        db.save_product_image_cache(cache_key, "ai", b"ai-image", "image/jpeg")
        db.init_db()

        restored = load_product("0898999000022")
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored["product_name"], "Coconut Water")
        self.assertEqual(restored["best_image_url"], "https://example.test/open-food-facts.jpg")
        self.assertNotIn("ai_image_url", restored)
        expected_profile = {
            **profile,
            "_guidance_version": AI_PROFILE_GUIDANCE_VERSION,
            "_service_input_signature": get_ai_food_profile_service_signature(),
        }
        self.assertEqual(restored["ai_food_profile"], expected_profile)
        self.assertTrue(restored["ai_food_profile_cached"])
        self.assertEqual(restored["_cached_off_image_data"], b"off-image")
        self.assertEqual(restored["_cached_ai_image_data"], b"ai-image")
        self.assertEqual(load_ai_profile(restored), expected_profile)

    def test_scanned_produce_uses_fresh_shelf_life_for_best_by(self):
        product = {
            "product_name": "Fresh strawberries",
            "categories": "Fresh produce",
            "ai_food_profile": {
                "shelf_life_days": {"fresh": 4, "unopened": None, "opened": None},
                "storage": "Fresh produce: refrigerate and keep dry.",
            },
        }

        draft = scanned_product_draft(product)

        self.assertEqual(draft["safety_class"], "fresh_produce")
        self.assertEqual(
            draft["best_by"],
            (date.today() + timedelta(days=4)).isoformat(),
        )

    def test_best_by_suggestion_matches_food_state_and_uses_default_when_missing(self):
        shelf_life_days = {"fresh": 4, "unopened": 20, "opened": 6}
        today = date(2026, 10, 20)

        self.assertEqual(
            _suggested_best_by(shelf_life_days, "fresh_produce", today=today),
            "2026-10-24",
        )
        self.assertEqual(
            _suggested_best_by(shelf_life_days, "sealed_packaged", today=today),
            "2026-11-09",
        )
        self.assertEqual(
            _suggested_best_by(shelf_life_days, "homemade_or_opened", today=today),
            "2026-10-26",
        )
        self.assertEqual(
            _suggested_best_by({}, "sealed_packaged", today=today),
            (today + timedelta(days=DEFAULT_BEST_BY_DAYS)).isoformat(),
        )

    def test_changed_ai_service_signature_clears_only_cached_profiles(self):
        product = {
            "code": "0898999000022",
            "product_name": "Coconut Water",
            "categories": "Beverages",
        }
        store_product(product)
        store_ai_profile(
            product,
            {
                "risk": "Low Risk",
                "storage": "After opening: refrigerate.",
                "_provider": "remote",
            },
        )
        cache_key = str(product["_product_cache_key"])
        db.save_product_image_cache(cache_key, "ai", b"ai-image", "image/jpeg")

        cleared = db.clear_stale_product_ai_profiles("different-service-signature")
        restored = load_product("0898999000022")

        self.assertEqual(cleared, 1)
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertNotIn("ai_food_profile", restored)
        self.assertEqual(restored["_cached_ai_image_data"], b"ai-image")

    def test_product_cache_hit_does_not_require_open_food_facts(self):
        product = {
            "code": "0898999000022",
            "product_name": "Coconut Water",
            "categories": "Beverages",
        }
        store_product(product)

        remote_calls = 0
        restored = load_product("898999000022")
        if restored is None:
            remote_calls += 1

        self.assertIsNotNone(restored)
        self.assertEqual(remote_calls, 0)

    def test_product_image_cache_resizes_and_compresses_images(self):
        image = np.full((1600, 2200, 3), (40, 120, 220), dtype=np.uint8)
        saved, encoded = cv2.imencode(".png", image)
        self.assertTrue(saved)

        cached_image = prepare_image_for_cache(encoded.tobytes())

        self.assertIsNotNone(cached_image)
        assert cached_image is not None
        decoded = cv2.imdecode(np.frombuffer(cached_image, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertLessEqual(max(decoded.shape[:2]), 1024)
        self.assertLessEqual(len(cached_image), db.PRODUCT_IMAGE_CACHE_MAX_ITEM_BYTES)

    def test_product_image_cache_enforces_count_and_byte_limits(self):
        with (
            patch.object(db, "PRODUCT_IMAGE_CACHE_MAX_COUNT", 3),
            patch.object(db, "PRODUCT_IMAGE_CACHE_MAX_BYTES", 10),
            patch.object(db, "PRODUCT_IMAGE_CACHE_MAX_ITEM_BYTES", 10),
        ):
            for index in range(4):
                db.save_product_image_cache(
                    f"barcode:{index}",
                    "ai",
                    bytes([index]) * 4,
                    "image/jpeg",
                )

            count, total_bytes = db.get_product_image_cache_stats()
            self.assertEqual(count, 2)
            self.assertEqual(total_bytes, 8)
            self.assertEqual(db.load_product_image_cache("barcode:0"), {})
            self.assertEqual(db.load_product_image_cache("barcode:3")["ai"], bytes([3]) * 4)


if __name__ == "__main__":
    # verbosity=2 prints each test name with 'ok' or 'FAIL' next to it.
    unittest.main(verbosity=2)
