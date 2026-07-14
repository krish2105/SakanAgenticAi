"""Provider-agnostic transactional email.

Default provider is "console": emails are logged, not sent -- so password
reset and email verification work end-to-end in local dev and on a free
deployment with zero email credentials (the reset/verify link shows up in the
logs). Set EMAIL_PROVIDER=smtp + the EMAIL_SMTP_* vars to deliver via any SMTP
relay (Postmark, SES, Gmail app-password, etc.), or EMAIL_PROVIDER=resend +
RESEND_API_KEY for Resend's HTTP API (free tier: 3,000 emails/month,
permanent, no card -- resend.com/signup). Swapping in another vendor HTTP API
later means adding one more branch here and nothing else.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("sakan.email")

EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "console").strip().lower()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Sakan AI <no-reply@sakan.ai>")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")


def _send_console(to: str, subject: str, body: str) -> None:
    log.info(
        "EMAIL (console provider -- not actually sent)\n  to: %s\n  subject: %s\n  body:\n%s",
        to,
        subject,
        body,
    )


def _send_smtp(to: str, subject: str, body: str) -> None:
    import smtplib
    from email.message import EmailMessage

    host = os.environ["EMAIL_SMTP_HOST"]
    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    username = os.environ.get("EMAIL_SMTP_USERNAME")
    password = os.environ.get("EMAIL_SMTP_PASSWORD")

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(msg)


def _send_resend(to: str, subject: str, body: str) -> None:
    import httpx

    if not RESEND_API_KEY:
        raise RuntimeError("EMAIL_PROVIDER=resend requires RESEND_API_KEY to be set.")

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": EMAIL_FROM, "to": [to], "subject": subject, "text": body},
        timeout=10,
    )
    response.raise_for_status()


def send_email(to: str, subject: str, body: str) -> None:
    """Best-effort: never raises into the caller (an auth flow shouldn't 500
    because email delivery hiccupped)."""
    try:
        if EMAIL_PROVIDER == "resend":
            _send_resend(to, subject, body)
        elif EMAIL_PROVIDER == "smtp":
            _send_smtp(to, subject, body)
        else:
            _send_console(to, subject, body)
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email to %s (subject=%r)", to, subject)


def send_verification_email(to: str, link: str) -> None:
    send_email(
        to,
        "Verify your Sakan AI email",
        f"Welcome to Sakan AI.\n\nVerify your email address:\n{link}\n\n"
        "If you didn't create this account, you can ignore this message.",
    )


def send_password_reset_email(to: str, link: str) -> None:
    send_email(
        to,
        "Reset your Sakan AI password",
        f"We received a request to reset your Sakan AI password.\n\n"
        f"Reset it here (link expires soon):\n{link}\n\n"
        "If you didn't request this, you can safely ignore this message.",
    )
