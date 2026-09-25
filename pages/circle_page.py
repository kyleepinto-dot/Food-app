"""My Circle screen for PantryIQ Connect (ported from Yaashvi's app).

Shows the Circle's members, pending invites, and an invite box. The Circle is the
trusted group that is the ONLY audience allowed to receive homemade/opened food
(the food-safety rule lives in db.py). Flet 0.85, shared shell, UI only.

Data contract (main.py supplies it):
  circle_name = str
  members  = list[dict]  # each: name, role ("owner"/…), relation, distance_mi, shared_count
  pending  = list[dict]  # each: invited_email, method, code, created_on
Callbacks:
  on_send_invite(contact: str)   on_copy_link()   on_resend(code)
"""

from __future__ import annotations

import flet as ft

from pages.theme import ThemeColors as T
from pages.shell_kit import app_shell, app_header


def _avatar(letter: str) -> ft.Container:
    return ft.Container(
        width=44, height=44, bgcolor=T.GREEN_SURFACE_SOFT, border_radius=999,
        alignment=ft.Alignment(0, 0),
        content=ft.Text(letter, weight=ft.FontWeight.BOLD, color=T.GREEN_TEXT),
    )


def _chip(text: str, bg: str, fg: str) -> ft.Container:
    return ft.Container(
        bgcolor=bg, border_radius=999, padding=ft.Padding(left=10, top=4, right=10, bottom=4),
        content=ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color=fg),
    )


def _member_card(m: dict) -> ft.Container:
    is_owner = str(m.get("role")) == "owner"
    if is_owner:
        subtitle = f"owner of this Circle · shared {int(m.get('shared_count') or 0)} items"
        tag = _chip("you", T.GREEN_SURFACE_SOFT, T.GREEN_TEXT)
    else:
        bits = []
        if m.get("relation"):
            bits.append(str(m["relation"]))
        if m.get("distance_mi") is not None:
            bits.append(f"{m['distance_mi']} mi")
        bits.append(f"shared {int(m.get('shared_count') or 0)} items")
        subtitle = " · ".join(bits)
        tag = _chip("active", "#E7F0E0", T.GREEN_TEXT)
    return ft.Container(
        bgcolor="#FFFFFF", border=ft.Border.all(1, "#E1E7E2"), border_radius=16, padding=14,
        content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            _avatar((str(m.get("name") or "?")[:1] or "?").upper()),
            ft.Column(expand=True, spacing=2, controls=[
                ft.Text(str(m.get("name") or "Member"), size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                ft.Text(subtitle, size=13, color=T.TEXT_SECONDARY),
            ]),
            tag,
        ]),
    )


def _pending_card(inv: dict, on_resend) -> ft.Container:
    code = inv.get("code") or "—"
    return ft.Container(
        bgcolor="#FAF7EC", border=ft.Border.all(1.5, "#E6D5A8"), border_radius=16, padding=14,
        content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            _avatar("?"),
            ft.Column(expand=True, spacing=2, controls=[
                ft.Text(f"{inv.get('invited_email') or 'invitee'} — pending", size=15,
                        weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
                ft.Text(f"invited by {inv.get('method') or 'link'} · code {code} · {inv.get('created_on') or ''}",
                        size=13, color=T.TEXT_SECONDARY),
            ]),
            ft.Button(content=ft.Text("Resend", size=12), on_click=lambda _, c=code: on_resend(c),
                      style=ft.ButtonStyle(bgcolor="#FFFFFF", color="#8F6410",
                                           side=ft.BorderSide(1, "#E6D5A8"),
                                           shape=ft.RoundedRectangleBorder(radius=12))),
        ]),
    )


def build_circle_shell(
    metrics: dict, circle_name: str, members: list, pending: list,
    on_send_invite, on_copy_link, on_resend,
    on_home_click, on_scan_click, on_pantry_click, on_me_click,
    on_back_click=None, invite_error: str = "",
) -> ft.Container:
    """Render My Circle. UI only; data + callbacks are passed in."""
    invite_input = ft.TextField(
        hint_text="Phone number or email…", border_radius=12,
        border_color="#D8D4C6", focused_border_color=T.BRAND_PRIMARY,
    )
    error_text = ft.Text(invite_error, size=13, color="#B5402C", visible=bool(invite_error))

    def _send(_):
        contact = str(invite_input.value or "").strip()
        if not contact:
            error_text.value = "Type a phone number or email first."
            error_text.visible = True
            error_text.update()
            return
        on_send_invite(contact)

    member_count = len(members)
    members_block = [
        ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Text("My Circle", size=22, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            _chip(f"{member_count} member" + ("" if member_count == 1 else "s"),
                  T.GREEN_SURFACE_SOFT, T.GREEN_TEXT),
        ]),
    ]
    members_block += [_member_card(m) for m in members] or [
        ft.Text("No members yet.", size=13, color=T.TEXT_SECONDARY)]
    if pending:
        members_block.append(ft.Text("Pending invites", size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY))
        members_block += [_pending_card(inv, on_resend) for inv in pending]

    invite_card = ft.Container(
        bgcolor="#FFFFFF", border_radius=18, padding=16,
        content=ft.Column(spacing=10, controls=[
            ft.Text("Invite someone you trust", size=15, weight=ft.FontWeight.BOLD, color=T.TEXT_PRIMARY),
            invite_input, error_text,
            ft.Row(spacing=8, controls=[
                ft.Button(expand=True, content=ft.Text("Send invite", weight=ft.FontWeight.BOLD), on_click=_send,
                          style=ft.ButtonStyle(bgcolor=T.BRAND_PRIMARY, color="#FFFFFF",
                                               shape=ft.RoundedRectangleBorder(radius=13))),
                ft.Button(expand=True, content=ft.Text("Copy link"), on_click=lambda _: on_copy_link(),
                          style=ft.ButtonStyle(bgcolor="#FFFFFF", color=T.GREEN_TEXT,
                                               shape=ft.RoundedRectangleBorder(radius=13))),
            ]),
        ]),
    )

    trust_note = ft.Container(
        bgcolor="#F7E9C8", border_radius=14, padding=12,
        content=ft.Text("🔒 Only people in your Circle can ever receive your homemade or opened "
                        "food. Sealed, in-date food can also reach the wider community and food banks.",
                        size=12, color="#7A570E"),
    )

    controls = [
        app_header(metrics, f"{circle_name or 'My Circle'}", on_back_click),
        *members_block,
        invite_card,
        trust_note,
    ]
    return app_shell(metrics, controls, "me", on_home_click, on_scan_click, on_pantry_click, on_me_click)
