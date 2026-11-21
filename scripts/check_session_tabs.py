#!/usr/bin/env python3
"""Check that a tab follows the session when another tab changes it (#238).

Why this exists
---------------
The session token is kept in localStorage, which every tab of a browser
shares, but each tab holds its own idea of who is signed in. Before #238, a
tab whose session was changed elsewhere kept going: signed out in tab B, tab
A answered "Not authenticated" on its next action; signed in as the
accountant in tab B, tab A showed the admin's screens and sent the
accountant's token, and got "Access denied". About 25 failures of the first
user acceptance test (#203) came from it.

This script opens two tabs of one browser and replays both cases, plus a
token changed without the browser's storage event, which the request check in
api.ts catches. It fails when tab A does not end on the sign-in form or on the
new user's screen, or when tab A sends a request the API refuses with 403.

It needs a browser, a running app and two real accounts: an admin and an
accountant. CI runs it on every PR (#181), with Chromium.

Usage
-----
    python scripts/check_session_tabs.py \\
        --admin admin@example.com:PASSWORD --accountant accountant@example.com:PASSWORD

Options: --url (default http://localhost:3000/), --locale (en, the default, or
fr), --browser (msedge, the default, or chromium), --screenshots DIR (a PNG of
tab A after each step). Requires Playwright (pip install playwright).

Exit status 1 on the first step that fails.
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

NAMES = {
    "en": {"dashboard": "Go to Dashboard", "sign_out": "Sign out", "admin_only": "Demos",
           "accountant_only": "Payslips", "loads": "Invoices", "signed_out": "signed out in another tab",
           "signed_in": "You signed in from another tab", "switched": "You are now signed in as"},
    "fr": {"dashboard": "Accéder à mon espace", "sign_out": "Se déconnecter", "admin_only": "Démos",
           "accountant_only": "Bulletins de paie", "loads": "Factures", "signed_out": "déconnecté dans un autre onglet",
           "signed_in": "Connexion effectuée dans un autre onglet",
           "switched": "Vous êtes maintenant connecté en tant que"},
}


class Failure(Exception):
    pass


def sign_in(page, names, email, password):
    """From the public homepage, or straight from the sign-in form if it is showing."""
    if not page.locator('input[type="password"]').is_visible():
        page.get_by_role("button", name=names["dashboard"]).first.click()
    page.locator('input[type="email"]').fill(email)
    page.locator('input[type="password"]').fill(password)
    page.keyboard.press("Enter")


def nav_button(page, name):
    return page.get_by_role("navigation").get_by_role("button", name=name, exact=True)


def nav_has(page, name) -> bool:
    return nav_button(page, name).count() > 0


def says(page, text) -> bool:
    """True when the page shows `text`, such as in a toast."""
    return page.get_by_text(re.compile(text, re.I)).count() > 0


def expect(condition, what):
    if not condition:
        raise Failure(what)
    print(f"  ok  {what}")


def api_token(api, email, password):
    request = urllib.request.Request(api + "/api/login", method="POST",
                                     data=json.dumps({"email": email, "password": password}).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())["access_token"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--admin", required=True, metavar="EMAIL:PASSWORD")
    parser.add_argument("--accountant", required=True, metavar="EMAIL:PASSWORD")
    parser.add_argument("--url", default="http://localhost:3000/")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="for a token outside the browser (step 3)")
    parser.add_argument("--locale", choices=tuple(NAMES), default="en")
    parser.add_argument("--browser", choices=("msedge", "chromium"), default="msedge")
    parser.add_argument("--screenshots", type=Path, help="save a PNG of tab A after each step here")
    args = parser.parse_args()
    names = NAMES[args.locale]
    admin = args.admin.partition(":")[::2]
    accountant = args.accountant.partition(":")[::2]
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge" if args.browser == "msedge" else None)
        # One context is one browser profile: its tabs share localStorage.
        context = browser.new_context(viewport={"width": 1280, "height": 800},
                                      locale="en-US" if args.locale == "en" else "fr-FR")
        context.add_init_script(f"localStorage.setItem('dixpertia_locale', '{args.locale}')")
        tab_a, tab_b = context.new_page(), context.new_page()
        refused = []
        tab_a.on("response", lambda r: r.status == 403 and "/api/" in r.url and refused.append(r.url))

        def shot(name):
            if args.screenshots:
                tab_a.bring_to_front()
                tab_a.wait_for_timeout(700)  # let the screen's fade-in finish
                tab_a.screenshot(path=str(args.screenshots / f"{args.locale}-{name}.png"))

        try:
            print("Both tabs signed in as the admin")
            tab_a.goto(args.url)
            sign_in(tab_a, names, *admin)
            tab_a.get_by_role("button", name=names["sign_out"]).first.wait_for(timeout=15000)
            tab_b.goto(args.url)  # restores the session from the shared token, straight into the app
            tab_b.get_by_role("button", name=names["sign_out"]).first.wait_for(timeout=15000)
            expect(nav_has(tab_a, names["admin_only"]) and nav_has(tab_b, names["admin_only"]),
                   "A and B show the admin")

            print("1. Tab B signs out")
            tab_b.get_by_role("button", name=names["sign_out"]).first.click()
            tab_a.locator('input[type="password"]').wait_for(timeout=5000)
            expect(True, "A shows the sign-in form")
            expect(says(tab_a, names["signed_out"]), "A says it was signed out in another tab")
            expect(not nav_has(tab_a, names["admin_only"]), "A shows no admin screen")
            shot("1-signed-out-elsewhere")

            print("2. Tab B signs in as the accountant")
            sign_in(tab_b, names, *accountant)
            tab_b.get_by_role("button", name=names["sign_out"]).first.wait_for(timeout=15000)
            nav_button(tab_a, names["accountant_only"]).wait_for(timeout=8000)
            expect(nav_has(tab_a, names["accountant_only"]) and not nav_has(tab_a, names["admin_only"]),
                   "A now shows the accountant's screens")
            expect(says(tab_a, names["signed_in"]), "A says the sign-in happened in another tab")
            shot("2-switched-to-accountant")

            print("3. The token changes with no storage event, then tab A acts")
            # A tab is not told of its own writes: this stands for a missed
            # event. A's next request must notice, not act as someone else.
            tab_a.evaluate("t => localStorage.setItem('token', t)", api_token(args.api, *admin))
            # Invoices loads its list from the API as it opens: a request to make.
            nav_button(tab_a, names["loads"]).click()
            nav_button(tab_a, names["admin_only"]).wait_for(timeout=8000)
            expect(nav_has(tab_a, names["admin_only"]), "A follows the token and shows the admin")
            expect(says(tab_a, names["switched"]), "A says which account it now shows")
            shot("3-followed-without-event")

            expect(not refused, "A sent no request the API refused with 403" + (f": {refused}" if refused else ""))
        except (Failure, PlaywrightTimeout) as failure:
            # A wait that times out is a step that failed: tab A never showed what it should.
            print(f"FAILED: {str(failure).splitlines()[0]}")
            shot("failure")
            return 1
        finally:
            browser.close()
    print("Every step passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
