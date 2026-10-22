"""How e-mail reaches the SMTP server (#186).

Port 465 is TLS from the first byte (SMTPS), any other port upgrades with
STARTTLS; both verify the server's certificate, so the SMTP password is only
ever sent to the real server. smtplib is replaced by a recorder: nothing is
sent.
"""

import ssl

import pytest


class Recorder:
    """Stands in for smtplib.SMTP / SMTP_SSL and records what was asked of it."""

    calls: list = []

    def __init__(self, host, port, context=None, timeout=None):
        Recorder.calls.append(("connect", type(self).__name__, host, port, context, timeout))

    def starttls(self, context=None):
        Recorder.calls.append(("starttls", context))

    def login(self, user, password):
        Recorder.calls.append(("login", user))

    def send_message(self, msg):
        Recorder.calls.append(("send", msg["To"]))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class SMTP(Recorder):
    pass


class SMTP_SSL(Recorder):  # noqa: N801 - the name smtplib uses
    pass


@pytest.fixture
def smtp(monkeypatch):
    from app.core.config import settings
    from app.services import email

    Recorder.calls = []
    monkeypatch.setattr(email.smtplib, "SMTP", SMTP)
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", SMTP_SSL)
    monkeypatch.setattr(settings, "SMTP_HOST", "mail.example.tn")
    monkeypatch.setattr(settings, "SMTP_USER", "contact@example.tn")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "not-a-real-password")

    def send(port):
        monkeypatch.setattr(settings, "SMTP_PORT", port)
        assert email.send_email("someone@example.tn", "Subject", "Body") is True
        return Recorder.calls
    return send


def verifies_certificates(context):
    return (isinstance(context, ssl.SSLContext)
            and context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname)


def test_port_465_is_tls_from_the_start_and_verified(smtp):
    calls = smtp(465)
    kind, cls, host, port, context, timeout = calls[0]
    assert (kind, cls, host, port) == ("connect", "SMTP_SSL", "mail.example.tn", 465)
    assert verifies_certificates(context), "the server's certificate must be checked"
    assert timeout, "a stuck server must not hang the request"
    assert not any(c[0] == "starttls" for c in calls)
    assert ("send", "someone@example.tn") in calls


def test_port_587_upgrades_with_a_verified_starttls_before_login(smtp):
    calls = smtp(587)
    assert calls[0][:4] == ("connect", "SMTP", "mail.example.tn", 587)
    starttls = next(i for i, c in enumerate(calls) if c[0] == "starttls")
    login = next(i for i, c in enumerate(calls) if c[0] == "login")
    assert starttls < login, "the password is sent only after TLS is up"
    assert verifies_certificates(calls[starttls][1]), "STARTTLS must check the certificate"
