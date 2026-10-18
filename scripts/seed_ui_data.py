#!/usr/bin/env python3
"""Fill a fresh environment with a little invented data, through the API (#181).

The browser checks (check_accessibility.py, check_mobile_overflow.py) need
screens with rows in them: the sideways scroll #130 fixed only appeared on a
table with data. This creates a few clients, invoices at different steps of
the verification flow, supplier bills and leave requests, as the three
accounts would - so every rule the API and the database enforce applies, and
the data cannot drift from the schema the way a direct SQL seeder can.

Usage
-----
    python scripts/seed_ui_data.py --api http://127.0.0.1:8000 \\
        --admin EMAIL:PASSWORD --accountant EMAIL:PASSWORD --employee EMAIL:PASSWORD

Run once, on an empty environment: it does not check for existing rows. All
names and figures are invented. Exit status 1 on the first refused request.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, token: str | None = None, body: dict | None = None):
        request = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "Accept-Language": "en",
                     **({"Authorization": f"Bearer {token}"} if token else {})},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            sys.exit(f"{method} {path} refused ({error.code}): {error.read().decode(errors='replace')}")

    def sign_in(self, account: str) -> str:
        email, _, password = account.partition(":")
        return self.call("POST", "/api/login", body={"email": email, "password": password})["access_token"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    for role in ("admin", "accountant", "employee"):
        parser.add_argument(f"--{role}", required=True, metavar="EMAIL:PASSWORD")
    args = parser.parse_args()

    api = Api(args.api)
    admin, accountant, employee = (api.sign_in(a) for a in (args.admin, args.accountant, args.employee))
    today = date.today()

    clients = [
        api.call("POST", "/api/clients", admin, {
            "nom": name, "email": email, "telephone": "+216 70 000 000", "adresse": address})["id"]
        for name, email, address in [
            ("Société Méditerranéenne de Services Informatiques et de Conseil", "contact@smsic.example.tn",
             "Immeuble Les Berges du Lac, Rue du Lac Windermere, 1053 Tunis"),
            ("Atlas Logistics", "billing@atlas.example.com", "12 avenue Habib Bourguiba, Sfax"),
        ]
    ]

    lines = [
        [{"designation": "Security audit of the internal network, including the remote access gateway",
          "quantite": 5, "prix_unitaire": 1250, "taux_tva": 19}],
        [{"designation": "Cloud migration workshop", "quantite": 2, "prix_unitaire": 900, "taux_tva": 19},
         {"designation": "Support subscription, quarterly", "quantite": 1, "prix_unitaire": 3000, "taux_tva": 19}],
        [{"designation": "Custom development", "quantite": 12, "prix_unitaire": 480, "taux_tva": 7}],
        [{"designation": "Training day", "quantite": 1, "prix_unitaire": 650, "taux_tva": 19}],
    ]
    due = (today + timedelta(days=30)).isoformat()
    drafts = []
    for n, items in enumerate(lines):
        body = {"client_id": clients[n % 2], "date_echeance": due, "items": items}
        drafts.append(api.call("POST", "/api/invoices", admin, body)["id"])
    # One left as a draft, one in review, one approved, one approved and sent.
    for invoice in drafts[1:]:
        api.call("POST", f"/api/invoices/{invoice}/submit", admin)
    for invoice in drafts[2:]:
        api.call("POST", f"/api/invoices/{invoice}/approve", accountant)
    api.call("POST", f"/api/invoices/{drafts[3]}/send", admin)

    supplier = api.call("POST", "/api/suppliers", admin, {"nom": "Tunisie Télécom Entreprises"})["id"]
    for n, (days_ago, due_in, ttc) in enumerate([(40, -5, 1190.0), (10, 20, 357.0)], start=1):
        api.call("POST", "/api/supplier-invoices", accountant, {
            "supplier_id": supplier, "supplier_reference": f"TT-2026-{n:05d}",
            "date_emission": (today - timedelta(days=days_ago)).isoformat(),
            "date_echeance": (today + timedelta(days=due_in)).isoformat(),
            "montant_ht": round(ttc / 1.19, 3), "montant_ttc": ttc, "items": []})

    for token, start, length, reason in [
        (employee, 14, 5, "Family holiday"),
        (employee, 60, 1, ""),
        (accountant, 30, 3, "Personal matters"),
    ]:
        first = today + timedelta(days=start)
        api.call("POST", "/api/leave-requests", token, {
            "startDate": first.isoformat(), "endDate": (first + timedelta(days=length - 1)).isoformat(),
            "type": "Annual Leave", "reason": reason})

    print(f"Seeded {len(clients)} clients, {len(drafts)} invoices, 2 supplier bills, 3 leave requests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
