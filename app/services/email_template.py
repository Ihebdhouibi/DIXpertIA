"""Generate HTML e-mails for DI Xpertia (#211)."""

import html
from app.i18n import t


def t_html(key: str, locale: str | None = None, nl2br: bool = False, **params) -> str:
    """Format a message, escaping all values exactly once for safe HTML insertion."""
    safe_params = {}
    for k, v in params.items():
        escaped = html.escape(str(v))
        if nl2br:
            escaped = escaped.replace("\n", "<br>")
        safe_params[k] = escaped
    return t(key, locale, **safe_params)


def render_html_email(
    lang: str,
    title: str,
    message_html: str,
    action_url: str | None = None,
    action_text: str | None = None,
    footer_text: str = ""
) -> str:
    lang = "fr" if lang == "fr" else "en"

    button_html = ""
    if action_url and action_text:
        button_html = f"""
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
            <tr>
                <td align="center" bgcolor="#101314" style="border-radius: 6px;">
                    <a href="{html.escape(action_url)}" target="_blank"
                       style="font-size: 15px;
                              font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                              color: #ffffff; text-decoration: none; padding: 14px 24px;
                              border-radius: 6px; display: inline-block;
                              font-weight: bold;">
                        {html.escape(action_text)}
                    </a>
                </td>
            </tr>
        </table>
        <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                  font-size: 12px; color: #6b7280; margin-top: 10px;
                  word-break: break-all;">
            {html.escape(action_url)}
        </p>
        """

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>{html.escape(title)}</title>
    <style>
        @media (prefers-color-scheme: dark) {{
            .body-bg {{ background-color: #101314 !important; }}
            .card-bg {{ background-color: #1f2937 !important; }}
            .text-main {{ color: #f9fafb !important; }}
            .text-muted {{ color: #9ca3af !important; }}
            .divider {{ border-color: #374151 !important; }}
            .logo-ink {{ color: #f9fafb !important; }}
            .logo-brand {{ color: #C6F24E !important; }}
            .footer-bg {{ background-color: #101314 !important; }}
        }}
    </style>
</head>
<body class="body-bg"
      style="margin: 0; padding: 0; background-color: #f3f4f6;
             font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
           border="0" style="background-color: #f3f4f6;">
        <tr>
            <td align="center" style="padding: 40px 10px;">
                <table role="presentation" class="card-bg" width="100%"
                       cellspacing="0" cellpadding="0" border="0"
                       style="max-width: 600px; background-color: #ffffff;
                              border-radius: 8px;
                              box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <tr>
                        <td align="center"
                            style="padding: 30px 20px;
                                   border-bottom: 1px solid #e5e7eb;"
                            class="divider">
                            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                                        font-size: 24px; font-weight: 800;
                                        letter-spacing: -0.5px;">
                                <span class="logo-ink"
                                      style="color: #101314;
                                             font-family: 'Courier New', Courier, monospace;
                                             font-size: 22px;">&gt;_</span>
                                <span class="logo-ink" style="color: #101314;">DI </span>
                                <span class="logo-brand" style="color: #5C7A0A;">Xpertia</span>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h1 class="text-main"
                                style="margin: 0 0 20px 0; font-size: 22px;
                                       color: #101314; font-weight: bold;">
                                {html.escape(title)}
                            </h1>
                            <div class="text-main"
                                 style="font-size: 15px; color: #374151;
                                        line-height: 1.6;">
                                {message_html}
                            </div>
                            {button_html}
                        </td>
                    </tr>
                    <tr>
                        <td align="center" class="text-muted divider footer-bg"
                            style="padding: 20px 30px;
                                   background-color: #f9fafb;
                                   border-top: 1px solid #e5e7eb;
                                   border-radius: 0 0 8px 8px;
                                   font-size: 12px; color: #6b7280;">
                            <p style="margin: 0 0 10px 0;">{html.escape(footer_text)}</p>
                            <p style="margin: 0;">&copy; DI Xpertia</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
