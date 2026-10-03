"""Run audit SQL files against the database in READ-ONLY mode.

Usage (from the repository root):

    .venv/Scripts/python.exe docs/technical-audit/database-audit/01-requests/scripts/run_readonly.py \
        docs/technical-audit/database-audit/01-requests/sql/<file>.sql \
        docs/technical-audit/database-audit/11-evidence/<folder>/<file>.md

Safety
------
Every connection sets `default_transaction_read_only = on` before running
anything, so PostgreSQL itself rejects any INSERT / UPDATE / DELETE / DDL with
"cannot execute ... in a read-only transaction". Each query also runs in its own
transaction, which is rolled back afterwards.

SQL file format
---------------
Queries are separated by header comments of the form:

    -- @id: Q-DISC-001
    -- @purpose: what the query is for
    -- @expected: what a healthy result looks like
    SELECT ...;

The DATABASE_URL is read from the application settings (.env). It is never
printed: the output shows only host, port and database name.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402

HEADER = re.compile(r"^--\s*@(\w+):\s*(.*)$")


def parse(sql_text: str) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    for line in sql_text.splitlines():
        m = HEADER.match(line.strip())
        if m:
            key, value = m.group(1), m.group(2).strip()
            if key == "id":
                current = {"id": value, "purpose": "", "expected": "", "sql": []}
                blocks.append(current)
            elif current is not None:
                current[key] = value
            continue
        if current is not None:
            current["sql"].append(line)
    for b in blocks:
        b["sql"] = "\n".join(b["sql"]).strip()
    return [b for b in blocks if b["sql"]]


def fmt(value) -> str:
    if value is None:
        return "NULL"
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    sql_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    blocks = parse(sql_path.read_text(encoding="utf-8"))

    url = make_url(settings.DATABASE_URL)
    target = f"{url.get_backend_name()}://{url.host}:{url.port}/{url.database}"
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"options": "-c default_transaction_read_only=on"},
    )

    lines = [
        f"# Résultats — {sql_path.name}",
        "",
        f"- **Généré le :** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Cible :** `{target}` (identifiants masqués)",
        "- **Mode :** lecture seule (`default_transaction_read_only = on`, chaque requête annulée par rollback)",
        f"- **Source :** `{sql_path.as_posix()}`",
        "",
    ]

    with engine.connect() as conn:
        ro = conn.execute(text("SHOW default_transaction_read_only")).scalar()
        lines.append(f"- **Lecture seule confirmée par le serveur :** `{ro}`")
        lines.append("")
        conn.rollback()
        for b in blocks:
            lines += [f"## {b['id']}", "", f"**Objectif :** {b['purpose']}", ""]
            if b["expected"]:
                lines += [f"**Résultat attendu :** {b['expected']}", ""]
            lines += ["```sql", b["sql"], "```", ""]
            try:
                result = conn.execute(text(b["sql"]))
                cols = list(result.keys())
                rows = result.fetchall()
                lines.append(f"**Résultat observé :** {len(rows)} ligne(s)")
                lines.append("")
                if rows:
                    lines.append("| " + " | ".join(cols) + " |")
                    lines.append("|" + "---|" * len(cols))
                    for r in rows:
                        lines.append("| " + " | ".join(fmt(v) for v in r) + " |")
                lines.append("")
            except Exception as exc:  # report, do not crash the whole run
                lines += [f"**Résultat observé :** ERREUR — `{type(exc).__name__}: {str(exc).splitlines()[0]}`", ""]
            finally:
                conn.rollback()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(blocks)} requêtes -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
