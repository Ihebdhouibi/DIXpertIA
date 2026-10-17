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

It needs a browser, a running app and real accounts, so it is a local check,
run before a frontend PR that touches layout. It is not a pre-commit hook.

Usage
-----
    # the app on http://localhost:3000 and the API behind it
    python scripts/check_mobile_overflow.py \\
        --account admin@example.com:PASSWORD \\
        --account accountant@example.com:PASSWORD

Each --account is EMAIL:PASSWORD; pass one per role to cover its screens.
Options: --url (default http://localhost:3000/), --width (default 390).
Requires Playwright with Microsoft Edge (pip install playwright).

Exit status 1 if any screen is wider than the viewport.
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

# Sidebar entries that are not app screens: the public homepage has no
# sidebar to come back from, and the others are actions.
SKIP = {"Home", "Sign out", "Close navigation", "Close"}


def screens_of(page) -> list[str]:
    page.get_by_role("button", name="Open navigation").click()
    page.wait_for_timeout(400)
    labels = [t.strip() for t in page.get_by_role("dialog").get_by_role("button").all_inner_texts()]
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    return [label for label in labels if label and label not in SKIP]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--account", action="append", required=True, metavar="EMAIL:PASSWORD")
    parser.add_argument("--url", default="http://localhost:3000/")
    parser.add_argument("--width", type=int, default=390)
    args = parser.parse_args()

    failures, checked = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        for account in args.account:
            email, _, password = account.partition(":")
            for theme in ("light", "dark"):
                context = browser.new_context(viewport={"width": args.width, "height": 844}, color_scheme=theme)
                context.add_init_script(f"localStorage.setItem('dixpertia_theme', '{theme}')")
                page = context.new_page()
                page.goto(args.url)
                page.get_by_role("button", name="Go to Dashboard").first.click()
                page.locator('input[type="email"]').fill(email)
                page.locator('input[type="password"]').fill(password)
                page.keyboard.press("Enter")
                page.get_by_role("button", name="Open navigation").wait_for(timeout=15000)
                for label in screens_of(page):
                    page.get_by_role("button", name="Open navigation").click()
                    page.wait_for_timeout(400)
                    page.get_by_role("dialog").get_by_role("button", name=label, exact=True).first.click()
                    page.wait_for_timeout(1800)
                    width = page.evaluate("document.documentElement.scrollWidth")
                    checked += 1
                    ok = width <= args.width
                    print(f"{'PASS' if ok else 'FAIL'}  {theme:5}  {email:40}  {label:18}  {width}px")
                    if not ok:
                        failures.append((theme, email, label, width))
                context.close()
        browser.close()

    print(f"\n{checked - len(failures)}/{checked} screens fit {args.width}px")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
