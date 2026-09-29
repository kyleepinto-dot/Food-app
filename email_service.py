"""Send SharedPantry Circle-invite emails via Gmail SMTP.

Credentials are read from (in order):
  1. environment variables  SHAREDPANTRY_GMAIL_USER  and  SHAREDPANTRY_GMAIL_APP_PASSWORD
  2. a local  email_config.py  file with  GMAIL_USER  and  GMAIL_APP_PASSWORD

email_config.py is git-ignored, so real credentials never go into the repo.
Copy email_config.example.py to email_config.py and fill it in (see EMAIL-SETUP.md).

Nothing here ever raises: send_invite_email() always returns (ok, message) so the
app keeps working even if email isn't set up or the network is down.
"""

from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def looks_like_email(contact: str) -> bool:
    """True if the contact string is a plausible email address (not a phone #)."""
    return bool(_EMAIL_RE.match((contact or "").strip()))


def _credentials() -> tuple[str, str]:
    user = os.environ.get("SHAREDPANTRY_GMAIL_USER", "")
    pw = os.environ.get("SHAREDPANTRY_GMAIL_APP_PASSWORD", "")
    if user and pw:
        return user.strip(), pw.strip()
    try:
        import email_config  # local, git-ignored
        return (str(getattr(email_config, "GMAIL_USER", "")).strip(),
                str(getattr(email_config, "GMAIL_APP_PASSWORD", "")).strip())
    except Exception:
        return "", ""


def is_configured() -> bool:
    """True when a Gmail address + app password are available."""
    user, pw = _credentials()
    return bool(user and pw)


def _build_message(user: str, to_email: str, inviter_name: str,
                   circle_name: str, code: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"{inviter_name} invited you to their SharedPantry Circle"
    msg["From"] = user
    msg["To"] = to_email
    msg.set_content(
        f"Hi!\n\n"
        f"{inviter_name} invited you to join their Circle \"{circle_name}\" on "
        f"SharedPantry. It is a little app that helps households share and donate "
        f"extra food before it goes to waste.\n\n"
        f"Your invite code is: {code}\n\n"
        f"Just let {inviter_name} know you got this and they can add you to the Circle.\n\n"
        f"Thanks for helping reduce food waste!\n"
        f"The SharedPantry team\n"
    )
    return msg


def send_invite_email(to_email: str, inviter_name: str, circle_name: str,
                      code: str) -> tuple[bool, str]:
    """Send one Circle-invite email. Returns (ok, message). Never raises."""
    to_email = (to_email or "").strip()
    if not looks_like_email(to_email):
        return False, "not an email address"
    user, pw = _credentials()
    if not (user and pw):
        return False, "email not set up"
    try:
        msg = _build_message(user, to_email, inviter_name or "A friend",
                             circle_name or "My Circle", code or "")
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=20) as server:
            server.login(user, pw)
            server.send_message(msg)
        return True, "sent"
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail login failed (check the app password)"
    except Exception as exc:  # network, DNS, etc. — never crash the app
        return False, f"could not send ({type(exc).__name__})"
