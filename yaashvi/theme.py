"""
theme.py  —  SharedPantry's look-and-feel.

This file is ONLY about how things look: the colors, the sizes, and the
little reusable widget helpers (card, chip, buttons, the shelf-life bar).
These were moved here from the top of the original single-file app so any
screen can share the same styling by importing from theme.
"""

import flet as ft

# ---------------------------------------------------------------------------
# Design tokens (colors + sizes). Moved unchanged from the original app.
# ---------------------------------------------------------------------------
BG          = "#F6F4EE"   # page background
CARD        = "#FFFFFF"   # card background
CARD_BORDER = "#E3E0D5"   # card border
GREEN       = "#1E5B3C"   # primary green
GREEN_DARK  = "#1C4030"   # dark green text
GREEN_TINT  = "#E7F0E0"   # green tint / "ok" chip
BODY        = "#23281F"   # body text
SECONDARY   = "#6B7263"   # secondary text
INPUT_BORDER = "#D8D4C6"  # input border
TRACK       = "#EFEDE5"   # slider/progress track

RADIUS_CARD  = 14
RADIUS_INPUT = 10

# ---------------------------------------------------------------------------
# Small reusable UI helpers so the styling matches the design system
# ---------------------------------------------------------------------------
def card(content, padding=18):
    return ft.Container(
        content=content,
        bgcolor=CARD,
        border=ft.border.all(1, CARD_BORDER),
        border_radius=RADIUS_CARD,
        padding=padding,
    )


def chip(text, bg=GREEN_TINT, color=GREEN_DARK):
    return ft.Container(
        content=ft.Text(text, size=12.5, weight=ft.FontWeight.BOLD, color=color),
        bgcolor=bg,
        border_radius=999,
        padding=ft.Padding(12, 4, 12, 4),
    )


def field_label(text):
    return ft.Text(text, size=14, weight=ft.FontWeight.BOLD, color=BODY)


def primary_button(text, on_click):
    return ft.FilledButton(
        content=ft.Text(text, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=GREEN,
            shape=ft.RoundedRectangleBorder(radius=RADIUS_INPUT),
            padding=ft.Padding(18, 12, 18, 12),
        ),
    )


def secondary_button(text, on_click):
    return ft.OutlinedButton(
        content=ft.Text(text, weight=ft.FontWeight.BOLD, color=GREEN_DARK),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=CARD,
            side=ft.BorderSide(1.5, GREEN),
            shape=ft.RoundedRectangleBorder(radius=RADIUS_INPUT),
            padding=ft.Padding(16, 11, 16, 11),
        ),
    )


def small_button(text, on_click, color=GREEN, text_color=GREEN_DARK):
    """A compact outlined button used for per-item actions in the pantry list."""
    return ft.OutlinedButton(
        content=ft.Text(text, weight=ft.FontWeight.BOLD, color=text_color, size=12.5),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=CARD,
            side=ft.BorderSide(1.5, color),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding(10, 5, 10, 5),
        ),
    )


def progress_bar(fraction, color, width):
    """A thin shelf-life bar built from two fixed-size boxes (no flex, so it
    always lays out). 'fraction' (0..1) = how much shelf life has been used."""
    fraction = max(0.03, min(1.0, fraction))   # always show a sliver
    return ft.Container(
        width=width, height=8, bgcolor=TRACK, border_radius=4,
        content=ft.Container(width=width * fraction, height=8,
                             bgcolor=color, border_radius=4),
    )
