"""
session.py  —  remembers who is logged in, even after the app closes.

This is NOT the database. It's a tiny text file (session.txt) that holds just
one thing: the id of the user who is currently logged in. When the app starts,
it reads this file; if it finds a user id, it can skip the Welcome screen.

  save(user_id)  ->  write the id to the file   (called when you log in)
  load()         ->  read the id back, or None   (called when the app starts)
  clear()        ->  delete the file             (called when you log out)
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(HERE, "session.txt")


def save(user_id):
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        f.write(str(user_id))


def load():
    """Return the saved user id (an int), or None if nobody is logged in."""
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def clear():
    try:
        os.remove(SESSION_PATH)
    except FileNotFoundError:
        pass
