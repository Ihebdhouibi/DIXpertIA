from unittest.mock import patch


@patch("app.services.email.smtplib.SMTP")
def test_send_email_multipart_order(mock_smtp):
    from app.services.email import send_email
    from app.core.config import settings

    with patch.object(settings, "SMTP_FROM", "from@example.com"), \
         patch.object(settings, "SMTP_HOST", "smtp.example.com"), \
         patch.object(settings, "SMTP_PORT", 587), \
         patch.object(settings, "SMTP_USER", "user"), \
         patch.object(settings, "SMTP_PASSWORD", "password"):

        send_email("test@example.com", "Subject", "Plain text", html_text="<p>HTML</p>")

        msg = mock_smtp.return_value.send_message.call_args[0][0]

        assert msg.get_content_type() == "multipart/alternative"
        payloads = msg.get_payload()
        assert payloads[0].get_content_type() == "text/plain"
        assert payloads[1].get_content_type() == "text/html"


def test_t_html_escapes_once_and_handles_newlines():
    """
    Tests the actual t_html helper, ensuring:
    1. It escapes HTML entities exactly once (no &amp;lt;).
    2. It handles newlines correctly when nl2br=True.
    """
    from app.services.email_template import t_html

    malicious_input = "O'Brien <script>alert('xss')</script>\nLine 2 & <img src=x>"

    # nl2br=True simulates the contact form message behavior
    msg = t_html(
        "email.contact.html_message",
        "fr",
        nl2br=True,
        name=malicious_input,
        email="a@b.c",
        topic="x",
        message=malicious_input,
        link="https://a.com"
    )

    # Check that it is escaped exactly once
    assert "O&#x27;Brien" in msg
    assert "&lt;script&gt;" in msg
    assert "&amp;lt;" not in msg  # Ensure no double escaping

    # Check that newlines are converted to <br>
    assert "Line 2" in msg
    assert "<br>" in msg
    assert "\n" not in msg  # No raw newlines should remain in the HTML body


def test_render_html_email_sets_lang():
    """Ensures the HTML template sets the correct lang attribute for both languages."""
    from app.services.email_template import render_html_email

    # Test FR
    html_fr = render_html_email(lang="fr", title="Test", message_html="<p>Test</p>")
    assert '<html lang="fr">' in html_fr

    # Test EN
    html_en = render_html_email(lang="en", title="Test", message_html="<p>Test</p>")
    assert '<html lang="en">' in html_en
