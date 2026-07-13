"""Phase 0 -- fail-closed production safety.

config.py flips several dev-only conveniences into hard errors when
SAKAN_ENV=production. Because that validation runs at import time, the
startup-failure cases are exercised in a subprocess with a clean env; the
call-time webhook guards are exercised in-process via monkeypatch.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap


from app.routers import billing, whatsapp
from app.routers.deals import client_ip_key


def _import_config_with_env(**env) -> subprocess.CompletedProcess:
    """Import app.config in a subprocess with a controlled environment."""
    base = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    base.update({k: v for k, v in env.items() if v is not None})
    code = "import app.config"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd="/home/user/SakanAgenticAi/backend",
        env=base,
        capture_output=True,
        text=True,
    )


def test_production_requires_jwt_secret():
    result = _import_config_with_env(SAKAN_ENV="production")
    assert result.returncode != 0
    assert "JWT_SECRET_KEY must be set" in result.stderr


def test_production_requires_stripe_webhook_secret_when_stripe_on():
    result = _import_config_with_env(
        SAKAN_ENV="production", JWT_SECRET_KEY="x", STRIPE_SECRET_KEY="sk_test"
    )
    assert result.returncode != 0
    assert "STRIPE_WEBHOOK_SECRET is required" in result.stderr


def test_production_requires_whatsapp_app_secret_when_whatsapp_on():
    result = _import_config_with_env(
        SAKAN_ENV="production", JWT_SECRET_KEY="x", WHATSAPP_ACCESS_TOKEN="tok"
    )
    assert result.returncode != 0
    assert "WHATSAPP_APP_SECRET is required" in result.stderr


def test_production_boots_cleanly_with_secrets_present():
    result = _import_config_with_env(SAKAN_ENV="production", JWT_SECRET_KEY="a-real-secret")
    assert result.returncode == 0, result.stderr


def test_development_default_uses_insecure_fallback_not_a_crash():
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(
            "import app.config as c; assert not c.IS_PRODUCTION; "
            "assert c.JWT_SECRET_KEY.startswith('dev-only')"
        )],
        cwd="/home/user/SakanAgenticAi/backend",
        env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_whatsapp_signature_fails_closed_in_production_without_secret(monkeypatch):
    monkeypatch.setattr(whatsapp.config, "WHATSAPP_APP_SECRET", None)
    monkeypatch.setattr(whatsapp.config, "IS_PRODUCTION", True)
    # In dev this returns True (accept unverified); in prod it must reject.
    assert whatsapp.verify_signature(b"{}", None) is False

    monkeypatch.setattr(whatsapp.config, "IS_PRODUCTION", False)
    assert whatsapp.verify_signature(b"{}", None) is True


def test_client_ip_key_prefers_forwarded_for():
    class Req:
        headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}

    assert client_ip_key(Req()) == "203.0.113.7"


def test_client_ip_key_falls_back_to_socket_when_no_header():
    class Client:
        host = "127.0.0.1"

    class Req:
        headers: dict = {}
        client = Client()

    assert client_ip_key(Req()) == "127.0.0.1"


def test_billing_module_exposes_production_guard_branch():
    # Sanity: the webhook handler references config.IS_PRODUCTION so the
    # fail-closed branch is wired (full webhook flow covered in test_billing).
    import inspect

    assert "IS_PRODUCTION" in inspect.getsource(billing.stripe_webhook)
