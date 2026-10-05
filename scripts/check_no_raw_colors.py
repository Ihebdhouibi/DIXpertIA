#!/usr/bin/env python3
"""Reject colours that bypass the theme in frontend source files.

Why this exists
---------------
Every colour in the app comes from the token layer in src/index.css: brand
colours, semantic roles (surface, on-surface, primary, outline...) and status
tones, each with a light and a dark value (#23, #24, #80). A colour written
anywhere else ignores the brand and does not switch with the theme. Issue #25
removed about 170 of them; this hook keeps them from coming back.

What it rejects in src/**/*.ts, *.tsx and *.css
-----------------------------------------------
- hex literals (#137333, #fff) and rgb()/rgba()/hsl()/hsla() literals
- raw Tailwind palette classes: bg-red-50, text-emerald-600, border-gray-200...
- bg-white, text-white, border-white, bg-black, text-black, border-black,
  with or without an opacity modifier. Use the roles instead:
  surface-container-lowest, on-primary, on-error, outline-variant...

What it allows
--------------
- src/index.css: the one place colours are defined (not scanned). Other
  stylesheets, such as src/styles/calendar.css, must use its tokens (#79).
- Comments. Issue references (#104) and colours quoted in a comment are
  documentation, not styling.
- Scrims: bg-black/NN behind modals and drawers. They dim whatever is beneath
  and read correctly in both themes.
- The public homepage (src/components/Homepage.tsx) may use white surfaces:
  it keeps a fixed ink/paper composition and is not themed (#30, #80).
- Any line containing the marker `raw-color-ok:` followed by a reason, or the
  line just below such a marker. Use it sparingly and say why.

Usage
-----
    python scripts/check_no_raw_colors.py FILE [FILE ...]

Exits 1 and prints one line per offending colour if any are found.
"""

from __future__ import annotations

import re
import sys
from pathlib import PurePosixPath

PALETTE = (
    "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|"
    "teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose"
)
PREFIX = (
    "bg|text|border|border-[trblxy]|ring|ring-offset|outline|divide|fill|stroke|"
    "from|via|to|shadow|placeholder|accent|caret|decoration"
)

RULES = (
    ("hex colour", re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")),
    ("colour function", re.compile(r"\b(?:rgba?|hsla?)\(")),
    ("raw palette class", re.compile(rf"(?<![\w-])(?:{PREFIX})-(?:{PALETTE})-\d{{2,3}}\b")),
)
WHITE_BLACK = re.compile(r"(?<![\w-])(?:bg|text|border)-(?:white|black)(?:/\d+)?(?![\w-])")
SCRIM = re.compile(r"(?<![\w-])bg-black/\d+(?![\w-])")
MARKER = re.compile(r"raw-color-ok:\s*\S")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/")
LINE_COMMENT = re.compile(r"(?<![:\w])//.*$")

# Files that may use white surfaces because they are deliberately not themed.
UNTHEMED = {"src/components/Homepage.tsx"}


def strip_comments(line: str, in_block: bool) -> tuple[str, bool]:
    """Drop // and /* */ comments; carry an open block comment to the next line."""
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


def check(path: str) -> list[str]:
    posix = PurePosixPath(path.replace("\\", "/")).as_posix()
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path}: cannot read ({exc})"]

    problems = []
    in_block = False
    for number, raw in enumerate(lines, start=1):
        previous = lines[number - 2] if number > 1 else ""
        if MARKER.search(raw) or MARKER.search(previous):
            continue
        line, in_block = strip_comments(raw, in_block)
        for label, pattern in RULES:
            for match in pattern.finditer(line):
                problems.append(f"{path}:{number}: {label} {match.group(0)!r}")
        if posix.endswith(tuple(UNTHEMED)):
            continue
        for match in WHITE_BLACK.finditer(line):
            if SCRIM.fullmatch(match.group(0)):
                continue
            problems.append(f"{path}:{number}: fixed colour {match.group(0)!r} does not switch with the theme")
    return problems


def main(argv: list[str]) -> int:
    problems = [p for path in argv for p in check(path)]
    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} colour(s) bypass the theme. Use a token from src/index.css "
            "(semantic role or status tone), or add `raw-color-ok: <reason>` if it is truly intended."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
