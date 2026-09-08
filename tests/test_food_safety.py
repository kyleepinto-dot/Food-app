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

# Let Python find db.py / queries.py, which live one folder up from tests/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db     # noqa: E402


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


if __name__ == "__main__":
    # verbosity=2 prints each test name with 'ok' or 'FAIL' next to it.
    unittest.main(verbosity=2)
