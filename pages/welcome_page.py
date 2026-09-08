"""Welcome / login screen for PantryIQ Connect (ported from Yaashvi's app).

Two modes that toggle:
  "signin" -> email + password to log into an existing account
  "create" -> name + email + password to make a NEW account

Shown BEFORE login, so it has no bottom nav. Flet 0.85, UI only. The screen does
light empty/length validation, then hands valid values to on_submit; MAIN.PY calls
db.create_account / db.check_login and re-renders with `error` set on failure.

  on_submit({"mode", "name", "email", "password"})
  on_switch()   # flip signin <-> create
"""

from __future__ import annotations

import flet as ft

from pages.theme import ThemeColors as T


def _brand_chip(text: str) -> ft.Container:
    return ft.Container(
        bgcolor=T.BRAND_PRIMARY, border_radius=999,
        padding=ft.Padding(left=12, top=6, right=12, bottom=6),
        content=ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
    )


def build_welcome_shell(metrics: dict, mode: str, on_submit, on_switch, error: str = "") -> ft.Container:
    """Render the Welcome screen (sign in OR create account). UI only."""
    creating = mode == "create"

    err = ft.Text(error, size=13, color="#B5402C", visible=bool(error))

    def field(hint, password=False):
        return ft.TextField(
            hint_text=hint, password=password, can_reveal_password=password,
            border_radius=12, border_color="#D8D4C6", focused_border_color=T.BRAND_PRIMARY,
        )

    name_in = field("Your name")
    email_in = field("Email…")
    pw_in = field("Password…", password=True)

    def submit(_):
        email = str(email_in.value or "").strip()
        pw = str(pw_in.value or "")
        if creating:
            name = str(name_in.value or "").strip()
            if not name or not email or not pw:
                err.value = "Please fill in your name, email, and password."
                err.visible = True; err.update(); return
            if len(pw) < 4:
                err.value = "Pick a password at least 4 characters long."
                err.visible = True; err.update(); return
        else:
            if not email or not pw:
                err.value = "Please enter your email and password."
                err.visible = True; err.update(); return
        on_submit({"mode": mode, "name": str(name_in.value or "").strip(), "email": email, "password": pw})

    # ── brand panel (top) ──
    brand = ft.Container(
        bgcolor=T.GREEN_TEXT, border_radius=22, padding=24,
        content=ft.Column(spacing=14, controls=[
            ft.Row(spacing=12, controls=[
                ft.Container(width=44, height=44, bgcolor="#FFFFFF", border_radius=12, alignment=ft.Alignment(0, 0),
                             content=ft.Text("SP", size=18, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT)),
                ft.Text("SharedPantry", size=22, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ]),
            ft.Text("Know your food.\nWaste nothing.\nFeed your community.",
                    size=26 if metrics["is_desktop"] else 22, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text("Scan any food to check freshness & nutrition, track your pantry, get "
                    "recipe ideas — and pass on what you won't use to friends, neighbors, "
                    "and local food banks.", size=13, color="#CBD8CC"),
            ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
                _brand_chip("🔍 Food IQ Scanner"), _brand_chip("📦 Smart Pantry"), _brand_chip("🤝 Share & Donate"),
            ]),
        ]),
    )

    # ── sign-in / create card (below) ──
    title = "Create your account" if creating else "Welcome back"
    button_label = "Create account" if creating else "Sign in"
    card_controls: list[ft.Control] = [ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY)]
    if creating:
        card_controls.append(name_in)
    card_controls += [
        email_in, pw_in, err,
        ft.Button(content=ft.Text(button_label, weight=ft.FontWeight.BOLD), on_click=submit,
                  style=ft.ButtonStyle(bgcolor=T.BRAND_PRIMARY, color="#FFFFFF",
                                       shape=ft.RoundedRectangleBorder(radius=13))),
        ft.Row(spacing=4, alignment=ft.MainAxisAlignment.CENTER, controls=[
            ft.Text("Already have an account?" if creating else "New here?", size=13, color=T.TEXT_SECONDARY),
            ft.Container(on_click=lambda _: on_switch(),
                         content=ft.Text("Sign in" if creating else "Create an account",
                                         size=13, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT)),
        ]),
    ]
    card = ft.Container(bgcolor="#FFFFFF", border_radius=22, padding=24,
                        content=ft.Column(spacing=14, controls=card_controls))

    return ft.Container(
        width=metrics["shell_width"], height=metrics["shell_height"],
        bgcolor=T.GREEN_SURFACE, border_radius=34, padding=16,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=30, color=T.SHELL_SHADOW, offset=ft.Offset(0, 8)),
        content=ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, controls=[brand, card]),
    )
