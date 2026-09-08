"""
queries.py  —  data functions for reading/creating "Circle" information.

db.py owns the low-level stuff (building the database, accounts, the food-safety
rule). queries.py sits on top and answers app questions like "who is in my
Circle?" and "make an invite". Splitting them keeps each file focused: db.py =
the plumbing, queries.py = the questions the screens ask.

We reuse db.DB_PATH so both files talk to the SAME pantry.db file.
"""

import random
import string
import sqlite3

import db


def _connect():
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row      # so we can read columns by name
    return con


def _make_invite_code():
    """A short, friendly invite code like 'SP-7QX4K2'."""
    chars = string.ascii_uppercase + string.digits
    return "SP-" + "".join(random.choices(chars, k=6))


def get_or_create_circle(user_id, user_name="Member"):
    """Return the circle this user owns. Every account gets one at sign-up, but
    this also repairs any older account that somehow doesn't have one yet."""
    con = _connect()
    row = con.execute(
        "SELECT * FROM circles WHERE owner_id = ? ORDER BY id LIMIT 1", (user_id,)
    ).fetchone()
    if row is None:
        cur = con.execute(
            "INSERT INTO circles (name, owner_id) VALUES (?, ?)",
            (f"{user_name}'s Circle", user_id),
        )
        circle_id = cur.lastrowid
        con.execute(
            "INSERT INTO circle_members (circle_id, user_id, role) VALUES (?, ?, 'owner')",
            (circle_id, user_id),
        )
        con.commit()
        row = con.execute("SELECT * FROM circles WHERE id = ?", (circle_id,)).fetchone()
    con.close()
    return row


def get_circle_members(circle_id):
    """Everyone in the circle, plus how many items each has shared so far.
    The owner is listed first, then the rest by name."""
    con = _connect()
    rows = con.execute(
        """
        SELECT u.id, u.name, cm.role, cm.relation, cm.distance_mi,
               (SELECT COUNT(*) FROM shares s WHERE s.shared_by = u.id) AS shared_count
        FROM circle_members cm
        JOIN users u ON u.id = cm.user_id
        WHERE cm.circle_id = ?
        ORDER BY (cm.role = 'owner') DESC, u.name
        """,
        (circle_id,),
    ).fetchall()
    con.close()
    return rows


def get_pending_invites(circle_id):
    """Invites that haven't been accepted yet, newest first."""
    con = _connect()
    rows = con.execute(
        "SELECT * FROM circle_invites WHERE circle_id = ? AND status = 'pending' "
        "ORDER BY created_on DESC, id DESC",
        (circle_id,),
    ).fetchall()
    con.close()
    return rows


# ---------------------------------------------------------------------------
# Impact math  —  turning what you did into real numbers.
# ---------------------------------------------------------------------------
# The chain: every food item has a WEIGHT in grams. We add up the grams of the
# food you rescued (shared + donated), then:
#   grams -> pounds : divide by 453.592  (there are 453.592 grams in a pound)
#   pounds -> CO2   : multiply by 2.5    (growing, shipping, and trashing food
#                     makes greenhouse gas — on average about 2.5 lb of CO2 for
#                     every 1 lb of food, so rescuing a pound AVOIDS ~2.5 lb CO2)
# If an item never had its weight typed in, we ESTIMATE 400 g per item so the
# numbers still mean something. (Estimates are clearly just estimates.)
GRAMS_PER_POUND    = 453.592
EST_GRAMS_PER_ITEM = 400
CO2_LB_PER_LB_FOOD = 2.5


def _item_grams(weight_g, qty):
    if weight_g:
        return float(weight_g)
    return (qty or 1) * EST_GRAMS_PER_ITEM


def get_impact(user_id):
    """The four Impact numbers, all computed from the database."""
    con = _connect()
    meals_shared  = con.execute("SELECT COUNT(*) FROM shares WHERE shared_by = ?",
                                (user_id,)).fetchone()[0]
    items_donated = con.execute("SELECT COUNT(*) FROM donations WHERE donated_by = ?",
                                (user_id,)).fetchone()[0]

    grams = 0.0
    for r in con.execute(
        "SELECT p.weight_g AS w, p.qty AS q FROM shares s "
        "LEFT JOIN pantry_items p ON p.id = s.item_id WHERE s.shared_by = ?",
        (user_id,),
    ):
        grams += _item_grams(r["w"], r["q"])
    for r in con.execute(
        "SELECT p.weight_g AS w, COALESCE(p.qty, d.qty) AS q FROM donations d "
        "LEFT JOIN pantry_items p ON p.id = d.item_id WHERE d.donated_by = ?",
        (user_id,),
    ):
        grams += _item_grams(r["w"], r["q"])
    con.close()

    pounds = grams / GRAMS_PER_POUND
    return {
        "meals_shared":  meals_shared,
        "items_donated": items_donated,
        "pounds_saved":  pounds,
        "co2_avoided":   pounds * CO2_LB_PER_LB_FOOD,
    }


def get_recent_activity(user_id, limit=6):
    """Things you did (shared / donated / requested), newest first."""
    con = _connect()
    rows = []
    for r in con.execute("SELECT title, created_on FROM shares WHERE shared_by = ?",
                         (user_id,)):
        rows.append(("🤝", f'Shared {r["title"]}', r["created_on"]))
    for r in con.execute(
        "SELECT p.name AS item, f.name AS bank, d.created_on AS c FROM donations d "
        "JOIN pantry_items p ON p.id = d.item_id "
        "JOIN food_banks f ON f.id = d.food_bank_id WHERE d.donated_by = ?",
        (user_id,),
    ):
        rows.append(("🏦", f'Donated {r["item"]} to {r["bank"]}', r["c"]))
    for r in con.execute(
        "SELECT s.title AS t, rq.created_on AS c FROM requests rq "
        "JOIN shares s ON s.id = rq.share_id WHERE rq.requested_by = ?",
        (user_id,),
    ):
        rows.append(("🙋", f'Requested {r["t"]}', r["c"]))
    con.close()
    rows.sort(key=lambda t: t[2] or "", reverse=True)   # newest first (by full timestamp)
    # Show only the date part; the time was only needed for correct ordering.
    return [(emoji, text, str(ts).split(" ")[0]) for emoji, text, ts in rows[:limit]]


def get_circle_size(user_id):
    """How many people are in this user's Circle (including themselves)."""
    con = _connect()
    row = con.execute("SELECT id FROM circles WHERE owner_id = ? ORDER BY id LIMIT 1",
                      (user_id,)).fetchone()
    if row is None:
        con.close()
        return 0
    n = con.execute("SELECT COUNT(*) FROM circle_members WHERE circle_id = ?",
                    (row["id"],)).fetchone()[0]
    con.close()
    return n


def get_food_banks():
    """All partner food banks, nearest first."""
    con = _connect()
    rows = con.execute(
        "SELECT * FROM food_banks ORDER BY distance_mi, name"
    ).fetchall()
    con.close()
    return rows


def get_food_bank(bank_id):
    con = _connect()
    row = con.execute("SELECT * FROM food_banks WHERE id = ?", (bank_id,)).fetchone()
    con.close()
    return row


def get_incoming_donations(bank_id):
    """Donations headed to this food bank, with the item name and donor name."""
    con = _connect()
    rows = con.execute(
        """
        SELECT d.id, d.status, d.dropoff_window, d.qty, d.created_on,
               p.name AS item_name, u.name AS donor_name
        FROM donations d
        JOIN pantry_items p ON p.id = d.item_id
        JOIN users u        ON u.id = d.donated_by
        WHERE d.food_bank_id = ?
        ORDER BY (d.status = 'scheduled') DESC, d.id DESC
        """,
        (bank_id,),
    ).fetchall()
    con.close()
    return rows


def check_in_donation(donation_id):
    """The food bank confirms an item arrived: flip its status to 'checked_in'."""
    con = _connect()
    con.execute("UPDATE donations SET status = 'checked_in' WHERE id = ?", (donation_id,))
    con.commit()
    con.close()


def create_invite(circle_id, contact, invited_by):
    """Make an invite code and store a PENDING invite for a phone/email.
    Returns the new invite code so the screen can show it."""
    contact = contact.strip()
    method = "email" if "@" in contact else "text"   # an @ means it's an email
    code = _make_invite_code()
    con = _connect()
    con.execute(
        "INSERT INTO circle_invites (circle_id, invited_email, invited_by, code, method, status) "
        "VALUES (?, ?, ?, ?, ?, 'pending')",
        (circle_id, contact, invited_by, code, method),
    )
    con.commit()
    con.close()
    return code
