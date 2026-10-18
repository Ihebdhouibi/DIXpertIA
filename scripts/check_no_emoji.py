#!/usr/bin/env python3
"""Reject emoji and pictographic symbols in source files.

Why this exists
---------------
Commit 27145f8 added `print(f"\N{LEFT-POINTING MAGNIFYING GLASS} Login attempt ...")`
to the login handler. On Windows `sys.stdout.encoding` is cp1252 whenever stdout
is a pipe or a file rather than a UTF-8 console, so that character raises
UnicodeEncodeError and `POST /api/login` returned 500. It survived in the tree
from 2026-07-22 to 2026-09-18 because a UTF-8 console hides the fault; it only
appears once logs are redirected, which is what happens under a service wrapper,
in Docker, or in CI.

ruff has no rule for this, hence a local hook.

What it deliberately allows
---------------------------
Accented Latin text. The API returns French error messages ("Cet e-mail est
deja utilise", "Acces refuse", "Fiche de paie introuvable") and the UI contains
French copy. Those are legitimate content, not a portability hazard, and
flagging them would make the hook unusable. Typographic punctuation (en dash,
bullet, curly quotes) is allowed for the same reason.

Only pictographic symbols are rejected - the class of character that is both
non-essential and liable to break a cp1252 stream.

Usage
-----
    python scripts/check_no_emoji.py FILE [FILE ...]

Exits 1 and prints one line per offending character if any are found.
"""

from __future__ import annotations

import sys
import unicodedata

# Ranges that are pictographic rather than textual.
BLOCKED_RANGES = (
    (0x1F000, 0x1FAFF),  # emoticons, pictographs, transport, symbols & flags
    (0x2600, 0x27BF),    # misc symbols + dingbats (check mark, cross mark, warning)
    (0x2B00, 0x2BFF),    # misc symbols and arrows
    (0xFE00, 0xFE0F),    # variation selectors (the invisible half of emoji)
    (0x1F1E6, 0x1F1FF),  # regional indicators
)

# Characters inside the blocked ranges that are conventional text, not emoji.
ALLOWED_CODEPOINTS = {
    0x2610,  # ballot box
    0x2611,  # ballot box with check - used in markdown task lists
    0x2612,  # ballot box with x
}


def is_blocked(ch: str) -> bool:
    cp = ord(ch)
    if cp < 0x80 or cp in ALLOWED_CODEPOINTS:
        return False
    for low, high in BLOCKED_RANGES:
        if low <= cp <= high:
            return True
    # Catch-all for pictographs outside the ranges above. Category "So" is
    # "Symbol, other"; restricting to cp > 0x2100 keeps currency symbols,
    # degree signs and similar textual marks out of scope.
    return cp > 0x2100 and unicodedata.category(ch) == "So"


def check(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except (UnicodeDecodeError, OSError) as exc:
        return [f"{path}: could not read ({exc.__class__.__name__})"]

    problems = []
    for lineno, line in enumerate(lines, 1):
        for col, ch in enumerate(line, 1):
            if is_blocked(ch):
                name = unicodedata.name(ch, "unnamed")
                problems.append(f"{path}:{lineno}:{col}: U+{ord(ch):04X} {name}")
    return problems


def main(argv: list[str]) -> int:
    problems = []
    for path in argv:
        problems.extend(check(path))

    if not problems:
        return 0

    for p in problems:
        print(p)
    print()
    print(f"{len(problems)} emoji/pictographic character(s) found.")
    print("These break cp1252 stdout on Windows (see the login 500 in issue #34).")
    print("Use plain ASCII in log messages and source. Accented text is fine.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
