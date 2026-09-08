"""
db.py  —  everything that talks to the SQLite database (pantry.db).

main.py calls these functions to save, read, and update data. The shape of the
database (all the tables) lives in schema.sql; init_db() runs that file to build
them. pantry.db is created automatically next to this file the first time you
run the app.

Accounts & passwords: we NEVER save the real password. We save a scrambled
version (a "hash"). See _hash_password() below for the plain-words explanation.
"""

import os
import hmac
import hashlib
import sqlite3
from datetime import date, datetime


def _now():
    """A precise timestamp (down to microseconds) so 'recent activity' can be
    ordered newest-first even when several things happen on the same day."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

HERE        = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(HERE, "pantry.db")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")


# ---------------------------------------------------------------------------
# Build the database from schema.sql, upgrade any older pantry.db, seed a user
# ---------------------------------------------------------------------------
def init_db():
    con = sqlite3.connect(DB_PATH)

    # 0) The "shares" table changed shape for the Share flow (item_id is now
    #    optional, plus new columns). It has NEVER held data, so if an old-shape
    #    copy exists and is empty, drop it here so step 1 rebuilds it fresh from
    #    schema.sql. (We only ever drop it when it's empty — never lose data.)
    scols = [r[1] for r in con.execute("PRAGMA table_info(shares)").fetchall()]
    if scols and "safety_class" not in scols:
        if con.execute("SELECT COUNT(*) FROM shares").fetchone()[0] == 0:
            con.execute("DROP TABLE shares")

    # 1) Build every table from the blueprint. executescript() runs all the
    #    CREATE TABLE statements in schema.sql at once. Because they each say
    #    "IF NOT EXISTS", running this again never wipes your data.
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        con.executescript(f.read())

    # 2) Migrations: your pantry.db was made BEFORE this new design, so its
    #    pantry_items table is missing the new columns. "IF NOT EXISTS" above
    #    won't touch an existing table, so we add the columns by hand here.
    #    (ALTER TABLE ... ADD COLUMN gives every existing row the default value,
    #    so your 7 items simply become owned by the demo user, id 1.)
    cols = [r[1] for r in con.execute("PRAGMA table_info(pantry_items)").fetchall()]
    if "safety_class" not in cols:
        con.execute("ALTER TABLE pantry_items ADD COLUMN safety_class TEXT DEFAULT 'sealed_packaged'")
    if "owner_id" not in cols:
        con.execute("ALTER TABLE pantry_items ADD COLUMN owner_id INTEGER DEFAULT 1")
    if "weight_g" not in cols:
        con.execute("ALTER TABLE pantry_items ADD COLUMN weight_g INTEGER")
    if "source_key" not in cols:
        con.execute("ALTER TABLE pantry_items ADD COLUMN source_key TEXT")
    if "added_via_scan" not in cols:
        con.execute("ALTER TABLE pantry_items ADD COLUMN added_via_scan INTEGER DEFAULT 1")

    # Same idea for the users table: add the password columns if an older
    # pantry.db doesn't have them yet.
    ucols = [r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()]
    if "pw_salt" not in ucols:
        con.execute("ALTER TABLE users ADD COLUMN pw_salt TEXT")
    if "pw_hash" not in ucols:
        con.execute("ALTER TABLE users ADD COLUMN pw_hash TEXT")

    # Circle tables gained a few columns for the My Circle screen.
    mcols = [r[1] for r in con.execute("PRAGMA table_info(circle_members)").fetchall()]
    if "relation" not in mcols:
        con.execute("ALTER TABLE circle_members ADD COLUMN relation TEXT")
    if "distance_mi" not in mcols:
        con.execute("ALTER TABLE circle_members ADD COLUMN distance_mi REAL")
    icols = [r[1] for r in con.execute("PRAGMA table_info(circle_invites)").fetchall()]
    if "code" not in icols:
        con.execute("ALTER TABLE circle_invites ADD COLUMN code TEXT")
    if "method" not in icols:
        con.execute("ALTER TABLE circle_invites ADD COLUMN method TEXT")

    # Donate flow: food_banks gained distance/schedule; donations gained a
    # drop-off window.
    fcols = [r[1] for r in con.execute("PRAGMA table_info(food_banks)").fetchall()]
    if "distance_mi" not in fcols:
        con.execute("ALTER TABLE food_banks ADD COLUMN distance_mi REAL")
    if "schedule" not in fcols:
        con.execute("ALTER TABLE food_banks ADD COLUMN schedule TEXT")
    dcols = [r[1] for r in con.execute("PRAGMA table_info(donations)").fetchall()]
    if "dropoff_window" not in dcols:
        con.execute("ALTER TABLE donations ADD COLUMN dropoff_window TEXT")

    # Seed a couple of partner food banks (INSERT OR IGNORE by id = safe to
    # re-run). These are the partners the Donate screen lets you pick from.
    for fb in [
        (1, "Westside Food Bank",     "canned protein, rice", 1.4, "Sat 9–12"),
        (2, "Hope Community Kitchen", "produce, cereal",      2.1, "Daily 4–6"),
        (3, "St. Mary's Pantry",      "any sealed goods",     3.0, "Mon & Wed"),
    ]:
        con.execute(
            "INSERT OR IGNORE INTO food_banks (id, name, accepts, distance_mi, schedule) "
            "VALUES (?, ?, ?, ?, ?)", fb,
        )

    # NOTE: We no longer seed a demo user. Real people make their own accounts on
    # the Welcome screen now, so there is no fake "id 1" user anymore.

    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Passwords & accounts
# ---------------------------------------------------------------------------
def _hash_password(password, salt=None):
    """Scramble a password so we can check it later WITHOUT ever storing the
    real one.

    Why not just save the password? If someone ever peeked at the database file,
    they'd see everyone's real passwords — and people reuse passwords on other
    sites. So instead we save a "hash": a one-way scramble. It's easy to scramble
    a password, but practically impossible to un-scramble the hash back into the
    password. When you log in, we scramble what you typed and check it matches.

    The "salt" is a random value we mix in first, different for every user. It
    means two people with the same password still get different hashes, so an
    attacker can't use a pre-made list of common-password hashes.
    """
    if salt is None:
        salt = os.urandom(16)                      # 16 random bytes, brand new
    # pbkdf2 repeats the scramble 100,000 times on purpose — slow enough that
    # guessing millions of passwords becomes painfully expensive for an attacker.
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), dk.hex()                    # store both as text (hex)


def create_account(name, email, password):
    """Make a new user, hash their password, and give them their own Circle.
    Returns the new user's id. Raises ValueError if the email is already used."""
    name  = name.strip()
    email = email.strip().lower()
    con = sqlite3.connect(DB_PATH)

    # One account per email. (We check by hand; a friendly error is nicer here.)
    if con.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        con.close()
        raise ValueError("That email already has an account. Try signing in.")

    salt_hex, hash_hex = _hash_password(password)
    cur = con.execute(
        "INSERT INTO users (name, email, pw_salt, pw_hash) VALUES (?, ?, ?, ?)",
        (name, email, salt_hex, hash_hex),
    )
    user_id = cur.lastrowid

    # Give the new user their very own Circle, and make them its owner. Their
    # pantry is empty automatically, because pantry_items are filtered by owner.
    cur2 = con.execute(
        "INSERT INTO circles (name, owner_id) VALUES (?, ?)",
        (f"{name}'s Circle", user_id),
    )
    circle_id = cur2.lastrowid
    con.execute(
        "INSERT INTO circle_members (circle_id, user_id, role) VALUES (?, ?, ?)",
        (circle_id, user_id, "owner"),
    )

    con.commit()
    con.close()
    return user_id


def check_login(email, password):
    """Return the user's row if the email + password are correct, else None."""
    email = email.strip().lower()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    con.close()
    if row is None or not row["pw_hash"]:
        return None
    # Re-scramble what they typed using THIS user's stored salt, then compare.
    _, hash_hex = _hash_password(password, bytes.fromhex(row["pw_salt"]))
    # compare_digest checks safely (it doesn't leak timing hints to attackers).
    if hmac.compare_digest(hash_hex, row["pw_hash"]):
        return row
    return None


def get_user(user_id):
    """Look up one user by id (used to confirm a saved session is still valid)."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    con.close()
    return row


# ---------------------------------------------------------------------------
# Food-safety rule (the heart of the whole app) — kept HERE in db.py so there
# is exactly ONE place that decides where each kind of food may go.
# ---------------------------------------------------------------------------
def allowed_share_scopes(safety_class):
    """Return WHERE an item is allowed to go, based on its food-safety type.

        sealed_packaged    -> ["circle", "community", "food_bank"]   (anywhere)
        fresh_produce      -> ["circle", "community"]                (no donating)
        homemade_or_opened -> ["circle"]                             (Circle ONLY)

    WHY homemade/opened food is Circle-only: a sealed can from a store is safe
    for anyone — a stranger can read the label and trust the seal. But food you
    cooked, or a package that's already been opened, could have been left out,
    handled, or gone bad in ways a stranger can't check. So it may only go to
    people you personally know and trust: your Circle. That is the single rule
    the whole "share vs donate" system is built on.
    """
    if safety_class == "sealed_packaged":
        return ["circle", "community", "food_bank"]
    if safety_class == "fresh_produce":
        return ["circle", "community"]
    return ["circle"]   # homemade_or_opened (and anything unknown) is safest here


VALID_SAFETY = {"sealed_packaged", "fresh_produce", "homemade_or_opened"}


def create_share(shared_by, item_id, title, safety_class,
                 best_by=None, pickup_window=None):
    """Post a share. Returns the new share id.

    FOOD-SAFETY LOCK lives here: if this share comes from a real pantry item,
    the ITEM's own safety_class always wins. That means you can never take a
    homemade item and post it as 'sealed' to reach a wider (less safe) audience
    — the rule is enforced in the database, not just hidden in the screen.
    """
    con = sqlite3.connect(DB_PATH)
    if item_id is not None:
        row = con.execute(
            "SELECT safety_class FROM pantry_items WHERE id = ?", (item_id,)
        ).fetchone()
        if row is not None:
            safety_class = row[0] or "homemade_or_opened"
    if safety_class not in VALID_SAFETY:
        safety_class = "homemade_or_opened"          # unknown -> safest/narrowest

    scope = ",".join(allowed_share_scopes(safety_class))   # saved for reference
    cur = con.execute(
        """INSERT INTO shares
           (item_id, shared_by, title, safety_class, scope, best_by, pickup_window,
            status, created_on)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'available', ?)""",
        (item_id, shared_by, title, safety_class, scope, best_by, pickup_window, _now()),
    )
    share_id = cur.lastrowid
    con.commit()
    con.close()
    return share_id


# ---------------------------------------------------------------------------
# Visibility gate (food-safety) — WHO is allowed to see a given share.
# ---------------------------------------------------------------------------
def can_see_share(viewer_id, share_id):
    """Can this viewer see this share? This is the food-safety audience rule:

      * You always see your OWN shares.
      * If the food type reaches the 'community' (produce & sealed), anyone can
        see it.
      * Homemade/opened food reaches ONLY 'circle', so a viewer can see it just
        when they are a member of the SHARER's Circle.

    Because the rule lives here, no screen can accidentally show homemade food
    to a stranger — the gate decides, not the UI.
    """
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    share = con.execute(
        "SELECT shared_by, safety_class FROM shares WHERE id = ?", (share_id,)
    ).fetchone()
    if share is None:
        con.close()
        return False

    owner_id = share["shared_by"]
    if viewer_id == owner_id:
        con.close()
        return True
    if "community" in allowed_share_scopes(share["safety_class"]):
        con.close()
        return True

    # Homemade/opened -> circle only: is the viewer in the sharer's Circle?
    in_circle = con.execute(
        "SELECT 1 FROM circle_members cm JOIN circles c ON c.id = cm.circle_id "
        "WHERE c.owner_id = ? AND cm.user_id = ? LIMIT 1",
        (owner_id, viewer_id),
    ).fetchone()
    con.close()
    return in_circle is not None


# ---------------------------------------------------------------------------
# Donate rule (food-safety) — only SEALED, IN-DATE items may be donated.
# ---------------------------------------------------------------------------
def can_donate(safety_class, best_by_iso):
    """True only if an item is sealed/packaged AND still before its best-by date.

    WHY the rule is this strict: a food bank hands your item to a stranger who
    has to trust it blindly — they didn't watch you make it or store it. A sealed,
    in-date package can be trusted by anyone (the seal and the date prove it).
    Homemade or opened food can't be verified by a stranger, and expired food
    isn't safe to pass on — so both are refused. (Homemade food should be shared
    with your Circle instead, where people already trust you.)
    """
    if safety_class != "sealed_packaged":
        return False
    try:
        return date.fromisoformat(best_by_iso) >= date.today()
    except (TypeError, ValueError):
        return False


def donate_ineligible_reason(safety_class, best_by_iso):
    """A friendly sentence explaining WHY an item can't be donated."""
    if safety_class == "homemade_or_opened":
        return ("Homemade or opened food can't be donated — a food bank can't "
                "verify it's safe. Share it with your Circle instead.")
    if safety_class == "fresh_produce":
        return ("Fresh produce isn't accepted for food-bank donation here — "
                "share it with your Circle or Community instead.")
    # sealed, but the date failed
    return ("This item is past its best-by date, so it can't be donated. "
            "Consider composting it.")


def get_donatable_items(owner_id):
    """The user's in-pantry items that actually pass the can_donate rule."""
    return [it for it in get_items(owner_id)
            if can_donate(it["safety_class"], it["best_by"])]


def create_donation(donated_by, item_id, food_bank_id, dropoff_window=None):
    """Log a donation and take the item out of the pantry (status 'donated').
    Refuses (ValueError) if the item doesn't pass the food-safety rule — so the
    rule is enforced in the database, not just hidden by the screen."""
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT safety_class, best_by, qty FROM pantry_items WHERE id = ?", (item_id,)
    ).fetchone()
    if row is None:
        con.close()
        raise ValueError("That item no longer exists.")
    if not can_donate(row[0], row[1]):
        con.close()
        raise ValueError("That item can't be donated (food-safety rule).")

    cur = con.execute(
        """INSERT INTO donations
           (item_id, donated_by, food_bank_id, qty, dropoff_window, status, created_on)
           VALUES (?, ?, ?, ?, ?, 'scheduled', ?)""",
        (item_id, donated_by, food_bank_id, row[2], dropoff_window, _now()),
    )
    donation_id = cur.lastrowid
    # The item leaves the pantry, just like composting does.
    con.execute("UPDATE pantry_items SET status = 'donated' WHERE id = ?", (item_id,))
    con.commit()
    con.close()
    return donation_id


def save_item(name, best_by, qty, unit, location, notes,
              safety_class="sealed_packaged", owner_id=None,
              weight_g=None, added_on=None):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO pantry_items
           (owner_id, name, best_by, qty, unit, location, notes, safety_class,
            weight_g, added_on)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (owner_id, name, best_by.isoformat(), qty, unit, location, notes,
         safety_class, weight_g, (added_on or date.today()).isoformat()),
    )
    con.commit()
    con.close()


def get_items(owner_id=None):
    """Every in-pantry item belonging to one user, soonest-to-expire first."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM pantry_items "
        "WHERE owner_id = ? AND status = 'in_pantry' ORDER BY best_by ASC",
        (owner_id,),
    ).fetchall()
    con.close()
    return rows


def get_item(item_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM pantry_items WHERE id = ?", (item_id,)).fetchone()
    con.close()
    return row


def update_note(item_id, note):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE pantry_items SET notes = ? WHERE id = ?", (note, item_id))
    con.commit()
    con.close()


def discard_item(item_id):
    """Mark an item as composted/discarded so it leaves the pantry list."""
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE pantry_items SET status = 'composted' WHERE id = ?", (item_id,))
    con.commit()
    con.close()


def get_stats(owner_id=None):
    """Real counts for one user — used by Achievements and Profile."""
    con = sqlite3.connect(DB_PATH)
    total     = con.execute("SELECT COUNT(*) FROM pantry_items WHERE owner_id=?",
                            (owner_id,)).fetchone()[0]
    in_pantry = con.execute("SELECT COUNT(*) FROM pantry_items WHERE owner_id=? AND status='in_pantry'",
                            (owner_id,)).fetchone()[0]
    composted = con.execute("SELECT COUNT(*) FROM pantry_items WHERE owner_id=? AND status='composted'",
                            (owner_id,)).fetchone()[0]
    con.close()
    return {"total": total, "in_pantry": in_pantry, "composted": composted}
