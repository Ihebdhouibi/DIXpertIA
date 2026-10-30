#!/usr/bin/env python3
"""Check that no screen of the app scrolls sideways on a phone (#130).

Why this exists
---------------
On a 390px phone, every screen with a data table could be dragged sideways
onto an empty band: Invoices was 1101px wide, Users 776px. The tables were
contained, but their visually hidden labels (the sr-only caption and header
text) are position:absolute. With no positioned box around the scroll area,
they were placed against the page and widened it. The fix was one class in
ui/Table, and nothing in CI would have noticed it going missing again. This
script signs in as each account, opens every screen of the sidebar in light
and dark, and fails when the document is wider than the viewport.

It needs a browser, a running app and real accounts. Run it before a
frontend PR that touches layout; CI runs it on every PR as well (#181), with
Chromium. It is not a pre-commit hook.

Usage
-----
    # the app on http://localhost:3000 and the API behind it
    python scripts/check_mobile_overflow.py \\
        --account admin@example.com:PASSWORD \\
        --account accountant@example.com:PASSWORD

Each --account is EMAIL:PASSWORD; pass one per role to cover its screens.
Options: --url (default http://localhost:3000/), --width (default 390),
--browser (msedge, the default, or chromium), --screenshots DIR (a PNG of each
failing screen), --locale (en, the default, or fr: French is longer). Requires Playwright (pip install playwright).

Exit status 1 if any screen is wider than the viewport.
"""

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# The few controls found by name, per UI language (#135): French is longer
# than English, so both are checked. "skip" lists the sidebar entries that are
# not app screens: the public homepage has no sidebar to come back from, and
# the others are actions.
NAMES = {
    "en": {"dashboard": "Go to Dashboard", "open": "Open navigation",
           "skip": {"DI Xpertia", "Sign out", "Close navigation", "Close"}},
    "fr": {"dashboard": "Accéder à mon espace", "open": "Ouvrir la navigation",
           "skip": {"DI Xpertia", "Se déconnecter", "Fermer la navigation", "Fermer"}},
}
BRAND = re.compile(r"^DI\s*Xpertia$", re.I)


def norm(text: str) -> str:
    # collapses NBSP, newlines and repeated spaces
    return " ".join(text.replace("\u00a0", " ").split())


def screens_of(page, names: dict) -> list[str]:
    page.get_by_role("button", name=names["open"]).click()
    page.wait_for_timeout(400)
    labels = [norm(t) for t in page.get_by_role("dialog").get_by_role("button").all_inner_texts()]
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    return [
        label for label in labels
        if label and not BRAND.match(label) and label.casefold() not in names["skip"]
    ]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--account", action="append", required=True, metavar="EMAIL:PASSWORD")
    parser.add_argument("--url", default="http://localhost:3000/")
    parser.add_argument("--width", type=int, default=390)
    parser.add_argument("--locale", choices=tuple(NAMES), default="en", help="the UI language to check")
    parser.add_argument("--browser", choices=("msedge", "chromium"), default="msedge",
                        help="msedge locally; chromium in CI, where Edge is not installed")
    parser.add_argument("--screenshots", type=Path, help="save a PNG of each failing screen here")
    args = parser.parse_args()
    names = NAMES[args.locale]
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    failures, checked = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge" if args.browser == "msedge" else None)
        for account in args.account:
            email, _, password = account.partition(":")
            for theme in ("light", "dark"):
                context = browser.new_context(viewport={"width": args.width, "height": 844}, color_scheme=theme,
                                              locale="en-US" if args.locale == "en" else "fr-FR")
                context.add_init_script(f"localStorage.setItem('dixpertia_theme', '{theme}'); "
                                   f"localStorage.setItem('dixpertia_locale', '{args.locale}')")
                page = context.new_page()
                page.goto(args.url)
                page.get_by_role("button", name=names["dashboard"]).first.click()
                page.locator('input[type="email"]').fill(email)
                page.locator('input[type="password"]').fill(password)
                page.keyboard.press("Enter")
                page.get_by_role("button", name=names["open"]).wait_for(timeout=15000)
                for label in screens_of(page, names):
                    page.get_by_role("button", name=names["open"]).click()
                    page.wait_for_timeout(400)
                    page.get_by_role("dialog").get_by_role(
                           "button", name=re.compile(rf"^\s*{re.escape(label)}\s*$")
                    ).first.click()
                    page.wait_for_timeout(1800)
                    width = page.evaluate("document.documentElement.scrollWidth")
                    checked += 1
                    ok = width <= args.width
                    print(f"{'PASS' if ok else 'FAIL'}  {theme:5}  {email:40}  {label:18}  {width}px")
                    if not ok:
                        failures.append((theme, email, label, width))
                        if args.screenshots:
                            name = re.sub(r"[^A-Za-z0-9]+", "-", f"{theme}-{email}-{label}").strip("-")
                            page.screenshot(path=args.screenshots / f"overflow-{name}.png", full_page=True)
                context.close()
        browser.close()

    print(f"\n{checked - len(failures)}/{checked} screens fit {args.width}px")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
