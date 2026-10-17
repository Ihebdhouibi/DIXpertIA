#!/usr/bin/env python3
"""Audit the app's accessibility on every screen, in light and dark (#31).

Why this exists
---------------
#31 audited 44 screens with axe-core (WCAG 2.1 A/AA plus best practice) and
walked each one with the keyboard. axe found nothing; the keyboard and manual
checks found four gaps axe cannot see: no skip link, a calendar that told
status by colour only, motion that ignored the reduced-motion setting, and a
month field that lost its focus ring. This script repeats both automated parts
so they do not regress:

1. axe-core on the sign-in and forgot-password screens and on every sidebar
   screen of each account given, in light and dark;
2. a keyboard pass on each screen: Tab from the top, checking that the first
   stop is "Skip to content" and that every stop shows a focus ring.

It needs a browser, the running app and real accounts. Run it before a
frontend PR; CI runs it on every PR as well (#181), with Chromium. It changes
no data.

axe-core is fetched from cdnjs at a pinned version, and its SHA-256 is checked
before it is injected into the page. A different file is refused.

Usage
-----
    python scripts/check_accessibility.py \\
        --account admin@example.com:PASSWORD --account employee@example.com:PASSWORD

Options: --url (default http://localhost:3000/), --browser (msedge, the
default, or chromium), --screenshots DIR (a PNG of each failing screen).
Requires Playwright. Exit status 1 on any axe violation or keyboard failure.
"""

import argparse
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
AXE_SHA256 = "b511cd9dec01c76f4b2ad1723b66b6db37d4c2eb4ed199076e1829d9ee7b75e3"
RULES = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]
SKIP = {"Home", "Sign out"}

RUN_AXE = """async (rules) => (await axe.run(document, {runOnly: rules})).violations
  .map(v => `${v.id} (${v.impact}): ${v.help} - ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(', ')}`)"""
FOCUS = """() => { const e = document.activeElement; const s = getComputedStyle(e);
  const ring = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || (s.boxShadow && s.boxShadow !== 'none');
  const text = (e.innerText || e.getAttribute('aria-label') || e.id || '').trim().slice(0, 40);
  return {tag: e.tagName, text, ring}; }"""
# axe measures what is painted: wait until entrance animations (the sign-in
# card fades in) have finished, or it reports half-transparent text.
SETTLED = "() => Promise.all(document.getAnimations().map(a => a.finished.catch(() => null)))"


def load_axe() -> str:
    with urllib.request.urlopen(AXE_URL, timeout=30) as response:
        body = response.read()
    digest = hashlib.sha256(body).hexdigest()
    if digest != AXE_SHA256:
        sys.exit(f"axe-core download does not match its pinned SHA-256 ({digest}); refusing to run it.")
    return body.decode("utf-8")


def keyboard_failures(page) -> list[str]:
    """Tab from the top of the document; report a missing skip link and unringed stops."""
    page.evaluate("document.body.tabIndex = -1; document.body.focus(); document.body.removeAttribute('tabindex')")
    failures, first = [], None
    for index in range(80):
        page.keyboard.press("Tab")
        stop = page.evaluate(FOCUS)
        if stop["tag"] == "BODY":
            break
        key = (stop["tag"], stop["text"])
        if index == 0 and stop["text"] != "Skip to content":
            failures.append(f"first Tab stop is {stop['text']!r}, not 'Skip to content'")
        if first is None:
            first = key
        elif key == first:
            break
        if not stop["ring"]:
            failures.append(f"no visible focus on {stop['tag']} {stop['text']!r}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--account", action="append", required=True, metavar="EMAIL:PASSWORD")
    parser.add_argument("--url", default="http://localhost:3000/")
    parser.add_argument("--browser", choices=("msedge", "chromium"), default="msedge",
                        help="msedge locally; chromium in CI, where Edge is not installed")
    parser.add_argument("--screenshots", type=Path, help="save a PNG of each failing screen here")
    args = parser.parse_args()
    axe = load_axe()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    problems, checked = [], 0

    def audit(page, where: str, keyboard: bool = True):
        nonlocal checked
        checked += 1
        page.evaluate(SETTLED)
        page.wait_for_timeout(300)
        page.add_script_tag(content=axe)
        found = [f"axe: {v}" for v in page.evaluate(RUN_AXE, RULES)]
        if keyboard:
            found += [f"keyboard: {f}" for f in keyboard_failures(page)]
        print(f"{'PASS' if not found else 'FAIL'}  {where}")
        for f in found:
            print(f"        {f}")
        if found and args.screenshots:
            page.screenshot(path=args.screenshots / f"a11y-{re.sub(r'[^A-Za-z0-9]+', '-', where).strip('-')}.png",
                            full_page=True)
        problems.extend(f"{where}: {f}" for f in found)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge" if args.browser == "msedge" else None)
        for theme in ("light", "dark"):
            context = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=theme,
                                          locale="en-US")
            context.add_init_script(f"localStorage.setItem('dixpertia_theme', '{theme}')")
            page = context.new_page()
            page.goto(args.url)
            page.get_by_role("button", name="Go to Dashboard").first.click()
            page.locator('input[type="email"]').wait_for()
            audit(page, f"{theme:5}  visitor  Sign in", keyboard=False)
            page.get_by_role("button", name="Forgot password?").first.click()
            page.wait_for_timeout(600)
            audit(page, f"{theme:5}  visitor  Forgot password", keyboard=False)
            context.close()

            for account in args.account:
                email, _, password = account.partition(":")
                context = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=theme,
                                              locale="en-US")
                context.add_init_script(f"localStorage.setItem('dixpertia_theme', '{theme}')")
                page = context.new_page()
                page.goto(args.url)
                page.get_by_role("button", name="Go to Dashboard").first.click()
                page.locator('input[type="email"]').fill(email)
                page.locator('input[type="password"]').fill(password)
                page.keyboard.press("Enter")
                page.locator("aside").wait_for(timeout=15000)
                labels = [t.strip() for t in page.locator("aside button").all_inner_texts() if t.strip()]
                for label in [label for label in dict.fromkeys(labels) if label not in SKIP]:
                    page.locator("aside").get_by_role("button", name=label, exact=True).first.click()
                    page.wait_for_timeout(1500)
                    audit(page, f"{theme:5}  {email}  {label}")
                context.close()
        browser.close()

    print(f"\n{checked - len({p.split(':')[0] for p in problems})}/{checked} screens clean")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
