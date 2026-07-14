"""Provider-dispatch tests for app/services/email.py: console (default,
never raises), smtp, and resend -- plus the "never raises into the caller"
guarantee that auth flows depend on."""
import app.services.email as email_module


def test_console_provider_never_sends_only_logs(monkeypatch, caplog):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "console")
    with caplog.at_level("INFO"):
        email_module.send_email("user@example.com", "Subject", "Body")
    assert "not actually sent" in caplog.text
    assert "user@example.com" in caplog.text


def test_smtp_provider_dispatches_to_smtplib(monkeypatch):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.example.com")

    captured = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            captured["starttls"] = True

        def send_message(self, msg):
            captured["sent_to"] = msg["To"]
            captured["subject"] = msg["Subject"]

    import smtplib

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    email_module.send_email("user@example.com", "Subject", "Body")

    assert captured["host"] == "smtp.example.com"
    assert captured["sent_to"] == "user@example.com"
    assert captured["subject"] == "Subject"


def test_resend_provider_posts_to_resend_api(monkeypatch):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(email_module, "RESEND_API_KEY", "re_test_key")

    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)

    email_module.send_email("user@example.com", "Subject", "Body")

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test_key"
    assert captured["json"]["to"] == ["user@example.com"]
    assert captured["json"]["subject"] == "Subject"


def test_resend_provider_without_key_is_swallowed_not_raised(monkeypatch, caplog):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(email_module, "RESEND_API_KEY", None)

    with caplog.at_level("ERROR"):
        email_module.send_email("user@example.com", "Subject", "Body")  # must not raise

    assert "Failed to send email" in caplog.text


def test_send_email_never_raises_even_on_provider_exception(monkeypatch):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "smtp")

    def raising(*a, **k):
        raise ConnectionError("smtp relay unreachable")

    monkeypatch.setattr(email_module, "_send_smtp", raising)

    # An auth flow shouldn't 500 because email delivery hiccupped.
    email_module.send_email("user@example.com", "Subject", "Body")


def test_send_verification_email_includes_link(monkeypatch):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "console")
    captured = {}

    def fake_send(to, subject, body):
        captured.update(to=to, subject=subject, body=body)

    monkeypatch.setattr(email_module, "send_email", fake_send)

    email_module.send_verification_email("user@example.com", "https://sakan.ai/verify?token=abc")

    assert captured["to"] == "user@example.com"
    assert "https://sakan.ai/verify?token=abc" in captured["body"]


def test_send_password_reset_email_includes_link(monkeypatch):
    monkeypatch.setattr(email_module, "EMAIL_PROVIDER", "console")
    captured = {}

    def fake_send(to, subject, body):
        captured.update(to=to, subject=subject, body=body)

    monkeypatch.setattr(email_module, "send_email", fake_send)

    email_module.send_password_reset_email("user@example.com", "https://sakan.ai/reset?token=xyz")

    assert captured["to"] == "user@example.com"
    assert "https://sakan.ai/reset?token=xyz" in captured["body"]
