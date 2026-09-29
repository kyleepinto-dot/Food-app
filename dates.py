"""Tiny date helpers so the screens can show dates as MM-DD-YYYY (more intuitive)
while the database keeps them as ISO (YYYY-MM-DD) for sorting and comparisons."""

from __future__ import annotations

from datetime import date, datetime


def parse_mdy(text: str):
    """Parse 'MM-DD-YYYY' (or with slashes) into a date, or None if invalid."""
    text = (text or "").strip()
    for fmt in ("%m-%d-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
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
