-- ===========================================================================
-- SharedPantry database blueprint (schema)
-- ===========================================================================
-- This file describes every TABLE in the app. db.py runs it at startup.
--
-- "IF NOT EXISTS" means: only create the table if it isn't there yet. So it is
-- SAFE to run this file every time the app starts — it never deletes data.
--
-- Two words to know:
--   PRIMARY KEY  = the unique id number for each row (like a row's name tag).
--   FOREIGN KEY  = a column that POINTS to another table's id (the "link").
--                  e.g. pantry_items.owner_id points to users.id.
-- ===========================================================================


-- 1) users --------------------------------------------------------------------
-- One row per person who uses the app. Everything else is "owned by" a user.
-- We NEVER store the real password. Instead we store a "hash" of it (pw_hash)
-- plus a random "salt" (pw_salt). See db.py for what those mean.
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT,
    pw_salt    TEXT,      -- a random value mixed into the password before hashing
    pw_hash    TEXT,      -- the scrambled result — NEVER the password itself
    joined_on  TEXT DEFAULT (date('now'))
);


-- 2) circles ------------------------------------------------------------------
-- A "circle" is a small trusted group (like your family or close friends) that
-- shares food together. owner_id is the user who created the circle.
CREATE TABLE IF NOT EXISTS circles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    owner_id   INTEGER NOT NULL,
    created_on TEXT DEFAULT (date('now')),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);


-- 3) circle_members -----------------------------------------------------------
-- Which users belong to which circles. This is a "join table": each row links
-- ONE user to ONE circle. A user can be in many circles; a circle has many
-- users. This table is how we store that "many-to-many" relationship.
CREATE TABLE IF NOT EXISTS circle_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    circle_id   INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    role        TEXT DEFAULT 'member',      -- 'owner' or 'member'
    relation    TEXT,                       -- how you know them: family / neighbor / friend
    distance_mi REAL,                       -- roughly how far away they live (miles)
    joined_on   TEXT DEFAULT (date('now')),
    FOREIGN KEY (circle_id) REFERENCES circles(id),
    FOREIGN KEY (user_id)   REFERENCES users(id)
);


-- 4) circle_invites -----------------------------------------------------------
-- Invitations to join a circle that haven't been accepted yet. When someone
-- accepts, your app will add them to circle_members.
CREATE TABLE IF NOT EXISTS circle_invites (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    circle_id     INTEGER NOT NULL,
    invited_email TEXT NOT NULL,             -- the phone number OR email you invited
    invited_by    INTEGER NOT NULL,
    code          TEXT,                      -- the invite code we generate for them
    method        TEXT,                      -- 'text' (phone) or 'email'
    status        TEXT DEFAULT 'pending',    -- pending / accepted / declined
    created_on    TEXT DEFAULT (date('now')),
    FOREIGN KEY (circle_id)  REFERENCES circles(id),
    FOREIGN KEY (invited_by) REFERENCES users(id)
);


-- 5) pantry_items -------------------------------------------------------------
-- The food itself. This is your original table, now upgraded:
--   owner_id  -> WHOSE item it is (points to users.id).
--   weight_g  -> weight in grams, so later we can add up "food saved from waste".
--   status    -> where the item is in its life: in_pantry / shared / composted.
CREATE TABLE IF NOT EXISTS pantry_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id       INTEGER NOT NULL DEFAULT 1,
    name           TEXT NOT NULL,
    best_by        TEXT NOT NULL,             -- YYYY-MM-DD
    qty            INTEGER NOT NULL,
    unit           TEXT NOT NULL,
    location       TEXT NOT NULL,
    notes          TEXT,
    safety_class   TEXT DEFAULT 'sealed_packaged',
    weight_g       INTEGER,                   -- optional for now (can be empty)
    status         TEXT DEFAULT 'in_pantry',
    added_via_scan INTEGER DEFAULT 1,
    added_on       TEXT NOT NULL DEFAULT (date('now')),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);


-- 6) shares -------------------------------------------------------------------
-- When a user OFFERS a pantry item to others. One share = one item being given.
-- scope says who can see it; status tracks whether it's still available.
CREATE TABLE IF NOT EXISTS shares (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id       INTEGER,                    -- the pantry item, if shared from one (optional)
    shared_by     INTEGER NOT NULL,
    title         TEXT NOT NULL,              -- name & quantity, e.g. "Veggie pasta bake, serves 4"
    safety_class  TEXT NOT NULL DEFAULT 'homemade_or_opened',  -- decides the audience
    scope         TEXT,                       -- the audience list, saved for reference
    best_by       TEXT,                       -- "Made today", "Best by this week", ...
    pickup_window TEXT,                        -- "Today 5–7pm", "This weekend", ...
    status        TEXT DEFAULT 'available',   -- available / requested / accepted / handed_off
    created_on    TEXT DEFAULT (date('now')),
    FOREIGN KEY (item_id)   REFERENCES pantry_items(id),
    FOREIGN KEY (shared_by) REFERENCES users(id)
);


-- 7) requests -----------------------------------------------------------------
-- When a user ASKS for a shared item. request -> points to the share it wants.
CREATE TABLE IF NOT EXISTS requests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    share_id     INTEGER NOT NULL,
    requested_by INTEGER NOT NULL,
    status       TEXT DEFAULT 'pending',      -- pending / accepted / declined
    created_on   TEXT DEFAULT (date('now')),
    FOREIGN KEY (share_id)     REFERENCES shares(id),
    FOREIGN KEY (requested_by) REFERENCES users(id)
);


-- 8) messages -----------------------------------------------------------------
-- The chat / inbox. Each row is ONE message from one user to another. request_id
-- (optional) ties the chat to the request it's about. is_read powers an "unread"
-- count later.
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user  INTEGER NOT NULL,
    to_user    INTEGER NOT NULL,
    request_id INTEGER,                        -- which request this is about (optional)
    body       TEXT NOT NULL,
    is_read    INTEGER DEFAULT 0,              -- 0 = unread, 1 = read
    sent_on    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (from_user)  REFERENCES users(id),
    FOREIGN KEY (to_user)    REFERENCES users(id),
    FOREIGN KEY (request_id) REFERENCES requests(id)
);


-- 9) food_banks ---------------------------------------------------------------
-- Places you can donate sealed food to. These aren't tied to one user.
CREATE TABLE IF NOT EXISTS food_banks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    address     TEXT,
    accepts     TEXT,                          -- what they currently need, e.g. "canned protein, rice"
    distance_mi REAL,                          -- roughly how far away it is
    schedule    TEXT,                          -- drop-off times, e.g. "Sat 9–12"
    created_on  TEXT DEFAULT (date('now'))
);


-- 10) donations ---------------------------------------------------------------
-- A record of an item donated to a food bank. It links three things together:
-- the item, the user who gave it, and the food bank that received it.
CREATE TABLE IF NOT EXISTS donations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id      INTEGER NOT NULL,
    donated_by   INTEGER NOT NULL,
    food_bank_id INTEGER NOT NULL,
    qty            INTEGER DEFAULT 1,
    weight_g       INTEGER,
    dropoff_window TEXT,                        -- when to drop it off, e.g. "Sat 9–12"
    status         TEXT DEFAULT 'scheduled',    -- scheduled / checked_in
    created_on     TEXT DEFAULT (date('now')),
    FOREIGN KEY (item_id)      REFERENCES pantry_items(id),
    FOREIGN KEY (donated_by)   REFERENCES users(id),
    FOREIGN KEY (food_bank_id) REFERENCES food_banks(id)
);
