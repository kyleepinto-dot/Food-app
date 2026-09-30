"""Tiny date helpers so the screens can show dates as MM-DD-YYYY (more intuitive)
while the database keeps them as ISO (YYYY-MM-DD) for sorting and comparisons."""

from __future__ import annotations

from datetime import date, datetime


def parse_mdy(text: str):
    """Forgiving date parse. Accepts MM-DD-YYYY, MM/DD/YYYY, ISO YYYY-MM-DD, and
    slashes/single-digit months, so we can auto-reformat whatever the user typed.
    Returns a date, or None if it truly isn't a real date."""
    text = (text or "").strip()
    # Separator formats (dash or slash): 4-digit year first, then 2-digit year
    # (so "10-05-26" becomes 2026 automatically; Python maps 00-68 -> 2000-2068).
    for fmt in ("%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d", "%m-%d-%y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Pure digits: decide by LENGTH (avoids %Y being greedy) — 8 = MMDDYYYY, 6 = MMDDYY.
    if text.isdigit():
        fmt = {8: "%m%d%Y", 6: "%m%d%y"}.get(len(text))
        if fmt:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                return None
    return None


def iso_to_mdy(iso: str) -> str:
    """'2026-10-29' -> '10-29-2026'. Blank if it can't be parsed."""
    try:
        return date.fromisoformat(str(iso)).strftime("%m-%d-%Y")
    except Exception:
        return ""


def mdy_to_iso(text: str):
    """'10-29-2026' -> '2026-10-29', or None if invalid."""
    d = parse_mdy(text)
    return d.isoformat() if d else None
