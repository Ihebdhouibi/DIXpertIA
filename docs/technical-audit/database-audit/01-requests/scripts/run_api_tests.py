"""Runtime API tests for the database audit (phases 6 and 8).

Usage (repository root, backend running on 127.0.0.1:8000), with the
credentials of an admin account of the LOCAL database:

    $env:AUDIT_ADMIN_EMAIL = "<admin e-mail>"
    $env:AUDIT_ADMIN_PASSWORD = "<admin password>"   # optional, see below
    .venv/Scripts/python.exe docs/technical-audit/database-audit/01-requests/scripts/run_api_tests.py

Output: docs/technical-audit/database-audit/11-evidence/api-tests/api-tests.results.md

What it does
------------
Each test states an expected *secure* behaviour and records the observed one.
A test PROVES a finding when the observed behaviour differs from the secure one.

Order matters:
  Part A — tests that write nothing, or whose write fails and is rolled back.
           Run first, because Part B adds users and would change count()+1.
  Part B — creates AUDIT-TEST accounts and rows (writes to the local database,
           authorised on 2026-10-01), then runs the tests that need them.

Safety
------
* Every row created is tagged AUDIT-TEST: e-mail domain audit-test.example.com
  (RFC 2606, reserved and never delivered), names prefixed "AUDIT-TEST".
  Nothing is ever deleted; cleanup is a separate, explicit decision.
* Passwords for test accounts are random, generated at runtime and never written.
* Tokens, hashes and passwords are redacted from every recorded response body.
* The admin account is used read-only except for T-A07 (a create that is
  expected to fail and roll back).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

import bcrypt  # noqa: E402
from jose import jwt  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.leaves import LeaveRequest, LeaveStatus, LeaveType  # noqa: E402
from app.models.invoicing import Invoice  # noqa: E402
from app.models.user import User  # noqa: E402

BASE = "http://127.0.0.1:8000"
OUT = ROOT / "docs/technical-audit/database-audit/11-evidence/api-tests/api-tests.results.md"
# No personal default: the admin account is the one of whoever runs the audit.
ADMIN_EMAIL = os.getenv("AUDIT_ADMIN_EMAIL", "")
# Defaults to the public default of seed_users.py --admin. If it was changed, pass
# the real one through the environment; this script never writes it anywhere.
ADMIN_PASSWORD = os.getenv("AUDIT_ADMIN_PASSWORD", "Admin123!")  # noqa: S105

JWT_RE = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
results: list[dict] = []
created: list[str] = []


# ---------------------------------------------------------------- helpers
def redact(text: str) -> str:
    text = JWT_RE.sub("<JWT REDACTED>", text)
    text = re.sub(r'("tempPassword"\s*:\s*")[^"]*', r"\1<REDACTED>", text)
    text = re.sub(r'("access_token"\s*:\s*")[^"]*', r"\1<REDACTED>", text)
    text = re.sub(r"\$2[aby]\$\d\d\$[./\w]{53}", "<BCRYPT REDACTED>", text)
    return text


def call(method: str, path: str, body=None, token: str | None = None) -> tuple[int, str, float]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace"), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), (time.perf_counter() - t0) * 1000


def login(email: str, password: str) -> str | None:
    status, body, _ = call("POST", "/api/login", {"email": email, "password": password})
    return json.loads(body).get("access_token") if status == 200 else None


def record(tid, obs, purpose, expected, request, status, body, verdict, note=""):
    results.append({
        "id": tid, "obs": obs, "purpose": purpose, "expected": expected,
        "request": request, "status": status, "body": redact(body)[:600],
        "verdict": verdict, "note": note,
    })
    print(f"{tid:7} {verdict:28} HTTP {status}")


def db_user(email: str, role: str, active: bool, uid: str) -> str:
    """Create (or reuse) an AUDIT-TEST user directly in the database. Returns its password."""
    password = secrets.token_urlsafe(18)
    db = SessionLocal()
    try:
        # Looked up by id, not e-mail: a re-run must reuse the same row, never add one.
        u = db.get(User, uid)
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        if u is not None and u.firstName != "AUDIT-TEST":
            raise SystemExit(f"{uid} existe et n'est pas un compte AUDIT-TEST : arrêt, rien n'est modifié.")
        if u is None:
            u = User(id=uid, email=email, firstName="AUDIT-TEST", lastName=role, role=role,
                     hashedPassword=hashed, isActive=active, isVerified=True, createdAt=datetime.utcnow())
            db.add(u)
            created.append(f"users.id={uid} ({email}, role={role}, isActive={active})")
        else:
            u.email, u.hashedPassword, u.isActive, u.role = email, hashed, active, role
            created.append(f"users.id={u.id} ({email}) — compte AUDIT-TEST existant réutilisé "
                           "(mot de passe et isActive réinitialisés)")
        db.commit()
    finally:
        db.close()
    return password


# ---------------------------------------------------------------- part A
def part_a(admin_token: str):
    # T-A01 / T-A02 — leave decision endpoints without any token
    for tid, path in (("T-A01", "/api/leave-requests/999999/approve"), ("T-A02", "/api/leave-requests/999999/reject")):
        body = {"comment": "AUDIT-TEST"} if path.endswith("reject") else None
        s, b, _ = call("POST", path, body)
        record(tid, "OBS-006", "Décider d'un congé sans être authentifié.",
               "401 (authentification exigée).", f"POST {path} — sans jeton", s, b,
               "CONFIRMED" if s != 401 else "REFUTED",
               "Un 404 prouve que le traitement s'exécute sans authentification : l'id inexistant est cherché en base.")

    # T-A03 — create a leave request anonymously
    s, b, _ = call("POST", "/api/leave-requests", {"employeeId": "USR-001", "employeeName": "AUDIT-TEST"})
    record("T-A03", "OBS-008", "Créer une demande de congé anonymement, au nom d'un autre employé.",
           "401.", "POST /api/leave-requests — sans jeton, employeeId=USR-001", s, b,
           "CONFIRMED" if s != 401 else "REFUTED",
           "Un 500 prouve à la fois l'absence d'authentification et le plantage dû aux champs absents du modèle.")

    # T-A04 — /logs
    s, b, _ = call("GET", "/logs")
    record("T-A04", "—", "Endpoint /logs public.", "Information.", "GET /logs — sans jeton", s, b, "INFO")

    # T-A05 — devices with a valid admin token
    s, b, _ = call("GET", "/api/devices", token=admin_token)
    record("T-A05", "OBS-010", "Lister les appareils en tant qu'admin.", "200.",
           "GET /api/devices — jeton admin", s, b,
           "CONFIRMED" if s == 500 else ("REFUTED" if s == 200 else "OBSERVATION"),
           "Un 500 confirme `current_user['role']` sur un objet User.")

    # T-A06 — what /api/data returns to an admin (keys and counts only)
    s, b, _ = call("GET", "/api/data", token=admin_token)
    summary = b
    if s == 200:
        d = json.loads(b)
        user_keys = sorted(d["users"][0].keys()) if d.get("users") else []
        summary = json.dumps({k: len(v) for k, v in d.items()} | {"users[0].keys": user_keys})
    record("T-A06", "OBS-009", "Contenu de /api/data pour un admin : clés et volumes, sans valeurs.",
           "Aucune colonne secrète.", "GET /api/data — jeton admin", s, summary, "INFO")

    # T-A07 — create a user: id = USR-{count+1}
    s, b, _ = call("POST", "/api/users", {"email": "audit.t07@audit-test.example.com", "firstName": "AUDIT-TEST",
                                          "lastName": "T07", "role": "employee"}, token=admin_token)
    if s in (200, 201):
        created.append("users — compte créé par T-A07 (audit.t07@audit-test.example.com)")
    record("T-A07", "OBS-021", "Créer un compte en tant qu'admin, avec des id existants non contigus.",
           "201.", "POST /api/users — jeton admin", s, b,
           "CONFIRMED" if s == 500 else ("REFUTED" if s in (200, 201) else "OBSERVATION"),
           "Un 500 confirme la collision d'id `USR-{count()+1}`. Précondition au 2026-10-02 : 7 comptes "
           "(USR-001, 003, 005, 006 + AUDIT-TEST 008, 009, 010), donc l'id généré est USR-008, déjà pris. "
           "L'état naturel d'avant l'audit (4 comptes, donc USR-005 déjà pris) est prouvé par Q-INT-006.")

    # T-A08 — token forged with the hardcoded fallback secret
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    m = re.search(r'os\.getenv\("SECRET_KEY",\s*"([^"]+)"\)', src)
    if m:
        forged = jwt.encode({"sub": "USR-001", "role": "admin", "exp": datetime.utcnow() + timedelta(minutes=5)},
                            m.group(1), algorithm="HS256")
        s, b, _ = call("GET", "/api/data", token=forged)
        record("T-A08", "OBS-014", "Jeton forgé avec la clé de repli codée en dur dans le dépôt.",
               "401 (la clé de repli n'est pas celle utilisée).", "GET /api/data — jeton forgé", s, b,
               "CONFIRMED" if s == 200 else "REFUTED (configuration locale)",
               "REFUTED signifie seulement que **cet** environnement définit SECRET_KEY ; "
               "le risque reste entier pour tout déploiement qui ne la définirait pas.")

    # T-A09 — login response time: unknown account vs known account with a wrong password
    unknown, known = [], []
    for i in range(8):
        unknown.append(call("POST", "/api/login", {"email": f"nobody{i}@audit-test.example.com", "password": "x"})[2])
        known.append(call("POST", "/api/login", {"email": ADMIN_EMAIL, "password": f"wrong-{i}"})[2])
    note = (f"médiane compte inconnu = {statistics.median(unknown):.0f} ms ; "
            f"compte existant = {statistics.median(known):.0f} ms")
    record("T-A09", "OBS-018", "Énumération des comptes par le temps de réponse de la connexion.",
           "Temps comparables.", "8 × POST /api/login par cas", 401, note,
           "CONFIRMED" if statistics.median(known) > 3 * statistics.median(unknown) else "REFUTED", note)


# ---------------------------------------------------------------- part B
def part_b(admin_token: str):
    emp_pw = db_user("audit.employee@audit-test.example.com", "employee", True, "USR-008")
    acc_pw = db_user("audit.accountant@audit-test.example.com", "accountant", True, "USR-009")
    ina_pw = db_user("audit.inactive@audit-test.example.com", "employee", False, "USR-010")
    emp = login("audit.employee@audit-test.example.com", emp_pw)
    acc = login("audit.accountant@audit-test.example.com", acc_pw)
    if not emp or not acc:
        # Without these tokens every following call would silently run anonymously
        # and produce false verdicts. Stop instead.
        print("Connexion des comptes AUDIT-TEST impossible : partie B interrompue.")
        record("T-B00", "—", "Connexion des comptes de test.", "200.", "POST /api/login — USR-008, USR-009",
               0, f"employee={'ok' if emp else 'échec'}, accountant={'ok' if acc else 'échec'}", "BLOQUÉ")
        return

    # T-B01 — employee reads /api/data
    s, b, _ = call("GET", "/api/data", token=emp)
    summary = json.dumps({k: len(v) for k, v in json.loads(b).items()}) if s == 200 else b
    leaked = s == 200 and any(len(v) for k, v in json.loads(b).items() if k in ("users", "invoices", "leaveRequests"))
    record("T-B01", "OBS-009 · R-FAC-05 · R-USR-06", "Un employé lit /api/data (volumes par clé).",
           "Ni utilisateurs, ni factures, ni congés d'autrui.", "GET /api/data — jeton employee", s, summary,
           "CONFIRMED" if leaked else "OBSERVATION",
           "Les factures et les congés sont vides tant que T-B05 et T-B08 n'ont pas créé de lignes ; "
           "la clé `users` suffit à prouver la fuite.")

    # T-B02 / T-B03 — positive controls on the router
    for tid, path in (("T-B02", "/api/invoices"), ("T-B03", "/api/clients")):
        s, b, _ = call("GET", path, token=emp)
        record(tid, "contrôle", f"Un employé appelle {path}.", "403.", f"GET {path} — jeton employee", s, b,
               "CONTROL OK" if s == 403 else "CONFIRMED (contrôle absent)")

    # T-B04 — inactive account
    tok = login("audit.inactive@audit-test.example.com", ina_pw)
    record("T-B04", "OBS-011 · R-USR-03", "Connexion d'un compte désactivé (isActive = false).", "401.",
           "POST /api/login — USR-010", 200 if tok else 401, "jeton délivré" if tok else "refusé",
           "CONFIRMED" if tok else "REFUTED")

    # T-B05 — accountant creates a client and an invoice
    s, b, _ = call("POST", "/api/clients", {"nom": "AUDIT-TEST Client"}, token=acc)
    client_id = json.loads(b).get("id") if s == 200 else None
    if client_id:
        created.append(f"clients.id={client_id} (AUDIT-TEST Client)")
    for attempt in (1, 2):
        payload = {
            "client_id": client_id,
            "date_echeance": str(date.today() + timedelta(days=30)),
            "items": [{"designation": "AUDIT-TEST", "prix_unitaire": "100"}],
        }
        s, b, _ = call("POST", "/api/invoices", payload, token=acc)
        record(f"T-B05.{attempt}", "R-FAC-01 · OBS-020", f"La comptable crée une facture (tentative {attempt}).",
               "403 (création réservée à l'admin) ; à défaut, 200 avec un statut défini.",
               "POST /api/invoices — jeton accountant", s, b,
               "CONFIRMED" if s in (200, 500) else ("REFUTED" if s == 403 else "OBSERVATION"),
               "200 ou 500 = la comptable a pu atteindre la création ; 403 = règle appliquée ; autre = à analyser.")
    db = SessionLocal()
    try:
        rows = db.query(Invoice).filter(Invoice.client_id == client_id).all() if client_id else []
        for r in rows:
            created.append(f"invoices.id={r.id} ({r.numero}, statut={r.statut})")
        detail = json.dumps([
            {"id": r.id, "numero": r.numero, "statut": str(r.statut), "cree_par_id": r.cree_par_id}
            for r in rows
        ])
    finally:
        db.close()
    record("T-B05.db", "OBS-020", "État en base après les deux tentatives.",
           "Si l'API a répondu 500 : aucune ligne.", "SELECT invoices WHERE client_id = <AUDIT-TEST>", 0, detail,
           "CONFIRMED" if rows and any(r.statut is None for r in rows) else "OBSERVATION",
           "Des lignes au statut NULL après un 500 prouvent l'erreur après commit et le doublon.")

    # T-B06 — employee downloads an invoice PDF
    if rows:
        s, b, _ = call("GET", f"/api/invoices/{rows[0].numero}/download", token=emp)
        record("T-B06", "contrôle", "Un employé télécharge un PDF de facture.", "403.",
               "GET /api/invoices/{numero}/download — jeton employee", s, b[:200],
               "CONTROL OK" if s == 403 else "CONFIRMED (contrôle absent)")

    # T-B07 — reset token used as a session token
    call("POST", "/api/forgot-password", {"email": "audit.employee@audit-test.example.com"})
    db = SessionLocal()
    try:
        reset = db.query(User).filter(User.email == "audit.employee@audit-test.example.com").first().resetToken
    finally:
        db.close()
    s, b, _ = call("GET", "/api/data", token=reset) if reset else (0, "pas de jeton généré", 0)
    record("T-B07", "OBS-012", "Utiliser le jeton de réinitialisation comme jeton de session.", "401.",
           "GET /api/data — Bearer = resetToken de USR-008", s, b[:120],
           "CONFIRMED" if s == 200 else "REFUTED")

    # T-B08 — anonymous team member insert
    s, b, _ = call("POST", "/api/team-members", {"firstName": "AUDIT-TEST", "lastName": "Anonymous"})
    if s in (200, 201):
        created.append(f"team_members — {redact(b)[:120]}")
    record("T-B08", "OBS-007 · R-EQP-01", "Créer un membre d'équipe sans être authentifié.", "401.",
           "POST /api/team-members — sans jeton", s, b, "CONFIRMED" if s in (200, 201) else "REFUTED")

    # T-B09 — anonymous approval of a real pending leave
    db = SessionLocal()
    try:
        lr = LeaveRequest(employee_id="USR-008", date_debut=date.today(), date_fin=date.today(),
                          type_conge=LeaveType.PAYE, motif="AUDIT-TEST", statut=LeaveStatus.EN_ATTENTE)
        db.add(lr)
        db.commit()
        lid = lr.id
        created.append(f"leave_requests.id={lid} (AUDIT-TEST, statut EN_ATTENTE)")
    finally:
        db.close()
    s, b, _ = call("POST", f"/api/leave-requests/{lid}/approve")
    db = SessionLocal()
    try:
        after = db.get(LeaveRequest, lid).statut
    finally:
        db.close()
    record("T-B09", "OBS-006 · R-CNG-02", "Approuver anonymement une demande réelle, puis relire son statut en base.",
           "401 ; et si accepté, statut = APPROUVE.", f"POST /api/leave-requests/{lid}/approve — sans jeton", s,
           f"{b} | statut en base après appel : {after}",
           "CONFIRMED" if s == 200 else "REFUTED",
           "200 + statut inchangé (EN_ATTENTE) = absence d'authentification ET écriture sans effet.")


# ---------------------------------------------------------------- report
def write_report():
    lines = ["# Résultats — tests d'exécution de l'API", "",
             f"- **Exécuté le :** {datetime.now().isoformat(timespec='seconds')}",
             f"- **Cible :** `{BASE}` (backend local), base `dixpertia` locale",
             "- **Script :** `01-requests/scripts/run_api_tests.py`",
             "- **Jetons, hash et mots de passe :** masqués dans tous les corps de réponse", "",
             "## Synthèse", "", "| Test | Observation | Verdict | HTTP |", "|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['obs']} | {r['verdict']} | {r['status']} |" for r in results]
    lines += ["", "## Détail", ""]
    for r in results:
        lines += [f"### {r['id']} — {r['purpose']}", "",
                  f"- **Observation testée :** {r['obs']}",
                  f"- **Requête :** `{r['request']}`",
                  f"- **Résultat attendu (comportement sûr) :** {r['expected']}",
                  f"- **Résultat observé :** HTTP {r['status']}",
                  f"- **Verdict :** **{r['verdict']}**"]
        if r["note"]:
            lines.append(f"- **Lecture :** {r['note']}")
        lines += ["", "```text", r["body"], "```", ""]
    lines += ["## Données créées par ce script (marquées AUDIT-TEST, non supprimées)", ""]
    lines += [f"- {c}" for c in created] or ["- aucune"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"-> {OUT}")


def main() -> int:
    try:
        call("GET", "/openapi.json")
    except Exception as exc:  # noqa: BLE001
        print(f"Backend injoignable sur {BASE} : {exc}")
        return 1
    if not ADMIN_EMAIL:
        print("Définir AUDIT_ADMIN_EMAIL (compte admin de la base locale) avant de lancer les tests.")
        return 1
    admin = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin:
        print("Connexion admin impossible : le mot de passe par défaut a-t-il été changé ?")
        return 1
    part_a(admin)
    part_b(admin)
    write_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
