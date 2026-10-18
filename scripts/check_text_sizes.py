#!/usr/bin/env python3
"""Reject text-* and animate-* classes that Tailwind will not generate.

Why this exists
---------------
The views used text-h1, text-display, text-caption, text-body-lg and
text-body-sm for months while none of them was declared. Tailwind generates
nothing for an unknown class and says nothing either, so every page title
rendered at body size and no check noticed (#122). This hook makes an
undeclared text-* class fail the commit instead.

The same went for animations: animate-fade-in was used 13 times and
animate-scale-up once, and neither was declared, so nothing ever faded or
scaled (#141). animate-* classes are checked the same way.

What a text-* class may be
--------------------------
- a size: Tailwind's own (xs, sm, base, lg, xl, 2xl ... 9xl) or a token
  declared as --text-<name> in src/index.css;
- a colour: a token declared as --color-<name> in src/index.css, or
  white / black / transparent / current / inherit (whether those are allowed
  is the colour guard's business, scripts/check_no_raw_colors.py);
- an alignment, wrapping or overflow utility: left, center, right, justify,
  start, end, wrap, nowrap, balance, pretty, ellipsis, clip;
- an arbitrary value, text-[...], which Tailwind always generates.

What an animate-* class may be
------------------------------
- Tailwind's own: spin, ping, pulse, bounce, none;
- a token declared as --animate-<name> in src/index.css;
- an arbitrary value, animate-[...].

Raw palette classes (text-red-500) are left to the colour guard, so a single
mistake is reported once. Comments are ignored, and a template such as
`text-${tone}` cannot be checked statically and is skipped.

Usage
-----
    python scripts/check_text_sizes.py [FILE ...]

With no file, every src/**/*.ts and *.tsx is checked. The pre-commit hook runs
it that way: removing a token from src/index.css must fail on the components
that still use it, even though only the stylesheet changed.

Exits 1 and prints one line per unknown class.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS_CSS = ROOT / "src" / "index.css"

TAILWIND_SIZES = {"xs", "sm", "base", "lg", "xl"} | {f"{n}xl" for n in range(2, 10)}
KEYWORD_COLOURS = {"white", "black", "transparent", "current", "inherit"}
UTILITIES = {"left", "center", "right", "justify", "start", "end",
             "wrap", "nowrap", "balance", "pretty", "ellipsis", "clip"}
TAILWIND_ANIMATIONS = {"spin", "ping", "pulse", "bounce", "none"}
PALETTE = re.compile(
    r"^(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|"
    r"teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}$"
)

# text-<name>, optionally with an opacity (/60) or an important marker, not
# part of a longer word. Variants such as md: or hover: precede it with ":".
CLASS = re.compile(r"(?<![\w-])!?text-([a-z0-9][a-z0-9-]*)(?:/\d+)?(?![\w-])")
ANIMATION = re.compile(r"(?<![\w-])!?animate-([a-z0-9][a-z0-9-]*)(?![\w-])")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/")
LINE_COMMENT = re.compile(r"(?<![:\w])//.*$")


def declared(prefix: str) -> set[str]:
    """Names declared as --<prefix>-<name> in the token file, without sub-properties."""
    css = TOKENS_CSS.read_text(encoding="utf-8")
    names = set(re.findall(rf"--{prefix}-([a-z0-9-]+)\s*:", css))
    # --text-h1--line-height is a property of h1, not a token of its own.
    return {n for n in names if "--" not in n and not n.endswith("-")}


def strip_comments(line: str, in_block: bool) -> tuple[str, bool]:
    if in_block:
        end = line.find("*/")
        if end == -1:
            return "", True
        line = line[end + 2:]
    line = BLOCK_COMMENT.sub("", line)
    start = line.find("/*")
    if start != -1:
        return line[:start], True
    return LINE_COMMENT.sub("", line), False


def check(path: str, allowed: set[str], animations: set[str] = TAILWIND_ANIMATIONS) -> list[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path}: cannot read ({exc})"]
    problems = []
    in_block = False
    for number, raw in enumerate(lines, start=1):
        line, in_block = strip_comments(raw, in_block)
        for match in CLASS.finditer(line):
            name = match.group(1)
            if name in allowed or PALETTE.match(name):
                continue
            problems.append(f"{path}:{number}: unknown class 'text-{name}'")
        for match in ANIMATION.finditer(line):
            if match.group(1) not in animations:
                problems.append(f"{path}:{number}: unknown class 'animate-{match.group(1)}'")
    return problems


def main(argv: list[str]) -> int:
    allowed = (TAILWIND_SIZES | KEYWORD_COLOURS | UTILITIES
               | declared("text") | declared("color"))
    animations = TAILWIND_ANIMATIONS | declared("animate")
    paths = argv or sorted(str(p) for ext in ("ts", "tsx") for p in (ROOT / "src").rglob(f"*.{ext}"))
    problems = [p for path in paths for p in check(path, allowed, animations)]
    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} class(es) that Tailwind will not generate. Use a Tailwind size or "
            "animation, or declare the token as --text-<name>, --color-<name> or --animate-<name> "
            "in src/index.css."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
