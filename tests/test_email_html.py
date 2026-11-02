import html
from unittest.mock import patch



def test_send_email_multipart_order():
    from app.services.email import send_email

    with patch("smtplib.SMTP") as mock_smtp:
        send_email("test@example.com", "Subject", "Plain text", html_text="<p>HTML</p>")
        msg = mock_smtp.return_value.__enter__.return_value.send_message.call_args[0][0]

        assert msg.get_content_type() == "multipart/alternative"
        payloads = msg.get_payload()
        assert payloads[0].get_content_type() == "text/plain"
        assert payloads[1].get_content_type() == "text/html"


def test_html_escaping():
    from app.services.email_template import render_html_email

    malicious_name = "<script>alert('xss')</script>"
    safe_name = html.escape(malicious_name)

    html_body = render_html_email(
        lang="fr",
        title="Test",
        message_html=f"<p>Name: {safe_name}</p>"
    )

    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body


def test_t_html_escapes_all_params():
    from app.services.email_template import t_html

    msg = t_html("email.contact.html_message", "fr", name="<script>", email="a@b.c", topic="x", message="<img>", link="https://a.com")
    assert "<script>" not in msg
    assert "&lt;script&gt;" in msg
    assert "<img>" not in msg
    assert "&lt;img&gt;" in msg
