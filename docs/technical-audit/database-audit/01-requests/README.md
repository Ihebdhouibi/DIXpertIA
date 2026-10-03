# Requêtes, scripts et commandes de l'audit

Toutes les requêtes et commandes utilisées pendant l'audit sont conservées ici.
Leurs résultats sont archivés dans `11-evidence/`.

## Exécuter une requête

Depuis la racine du dépôt :

```powershell
.venv\Scripts\python.exe docs\technical-audit\database-audit\01-requests\scripts\run_readonly.py `
    docs\technical-audit\database-audit\01-requests\sql\<fichier>.sql `
    docs\technical-audit\database-audit\11-evidence\<dossier>\<fichier>.results.md
```

`run_readonly.py` impose trois garanties :
- `default_transaction_read_only = on` est appliqué à la connexion, ce qui fait
  rejeter par PostgreSQL toute écriture et tout DDL ;
- chaque requête est suivie d'un `ROLLBACK` ;
- l'URL de connexion n'est jamais affichée : seuls l'hôte, le port et la base
  apparaissent.

## Scripts

| Script | Rôle | Écrit en base ? | Preuves produites |
|---|---|---|---|
| `scripts/run_readonly.py` | exécute un fichier SQL en lecture seule, imposée par le serveur | **non** | `11-evidence/{schema,data-integrity,explain-plans,sql-results}/` |
| `scripts/run_constraint_probe.py` | 30 tentatives d'écriture invalides, dans des SAVEPOINT, sous une transaction **toujours annulée** ; plus une vérification de la liaison des ENUM | **non** : rollback, puis 0 ligne résiduelle vérifiée | `11-evidence/data-integrity/constraint-probe.results.md` |
| `scripts/run_api_tests.py` | 20 tests HTTP par rôle (backend démarré requis) | **oui**, base locale seulement, lignes `AUDIT-TEST`, autorisé le 2026-10-01 | `11-evidence/api-tests/api-tests.results.md` |

## Format d'un fichier SQL

Chaque requête est précédée de trois en-têtes : son identifiant, son objectif
(ce qu'elle vérifie) et le résultat attendu si tout va bien. Le résultat
observé est écrit par le script dans le fichier de preuve.

```sql
-- @id: Q-XXX-NNN
-- @purpose: ce que la requête vérifie
-- @expected: le résultat attendu si tout va bien
SELECT ...;
```

## Index

| Fichier | Requêtes | Phase | Résultats | État |
|---|---|---|---|---|
| `sql/01-discovery-overview.sql` | Q-DISC-001 → Q-DISC-011 (11) | 1 | `11-evidence/schema/01-discovery-overview.results.md` | ✅ exécuté le 2026-10-02 |
| `sql/02-schema-inventory.sql` | Q-SCH-001 → Q-SCH-013 (13) | 2 | `11-evidence/schema/02-schema-inventory.results.md` | ✅ exécuté le 2026-10-02 |
| `sql/03-data-integrity.sql` | Q-INT-001 → Q-INT-020 (20) | 5 | `11-evidence/data-integrity/03-data-integrity.results.md` | ✅ exécuté le 2026-10-02 |
| `sql/04-performance.sql` | Q-PERF-001 → Q-PERF-012 (12) | 7 | `11-evidence/explain-plans/04-performance.results.md` | ✅ exécuté le 2026-10-02 (17 requêtes, dont 5 sondes ajoutées) |
| `sql/05-security.sql` | Q-SEC-001 → Q-SEC-008 (8) | 6 | `11-evidence/sql-results/05-security.results.md` | ✅ exécuté le 2026-10-02 |

**Total : 64 requêtes.** Une fois le serveur rétabli, elles s'exécutent toutes
avec une seule commande :

```powershell
$A = "docs\technical-audit\database-audit"
@(
  @("01-discovery-overview", "schema"),
  @("02-schema-inventory",   "schema"),
  @("03-data-integrity",     "data-integrity"),
  @("04-performance",        "explain-plans"),
  @("05-security",           "sql-results")
) | ForEach-Object {
  .venv\Scripts\python.exe "$A\01-requests\scripts\run_readonly.py" "$A\01-requests\sql\$($_[0]).sql" "$A\11-evidence\$($_[1])\$($_[0]).results.md"
}
```

### Hypothèses que ces requêtes doivent trancher

| Hypothèse | Requête décisive |
|---|---|
| L'application se connecte en superutilisateur (OBS-016) | Q-DISC-003, Q-SEC-002 |
| Aucune migration n'a jamais été appliquée (OBS-003) | Q-DISC-009 |
| Aucune contrainte CHECK ; FK en `NO ACTION` (OBS-023) | Q-SCH-003, Q-SCH-004 |
| Aucune colonne de FK n'est indexée (OBS-030) | Q-SCH-007 |
| `primary_key=True, index=True` crée des index en double | Q-SCH-006 |
| Les ENUM stockent les **noms** Python (`BROUILLON`) et non les valeurs (`brouillon`). Si c'est le cas, `insert_invoices.py`, qui passe `"brouillon"`, échoue. | Q-SCH-009 → noms stockés **CONFIRMED** ; échec du script **REFUTED** : SQLAlchemy convertit la valeur (`constraint-probe.results.md`) |
| Le prochain `POST /api/users` génère un id déjà pris (OBS-021) | Q-INT-006 |
| Les e-mails sont uniques mais sensibles à la casse | Q-INT-004 |

## Commandes de la Discovery (hors SQL)

Ces commandes ont servi à établir les faits de la Discovery. Elles sont en
lecture seule. Leurs résultats sont cités dans les documents de `02-discovery/`.

| Objectif | Commande | Résultat |
|---|---|---|
| Lister les appels API du frontend | `grep -rn "fetch(" src` | 5 appels |
| Lister l'usage du `localStorage` | `grep -rn localStorage src` | 8 clés de données (`dixpertia_user`, `_payslips`, `_leave_requests`, `_team_members`, `_invoices`, `_projects`, `_users`, `_notifications`), plus `token` et `dixpertia_darkmode` |
| Routes réellement exposées | `GET http://127.0.0.1:8000/openapi.json` (2026-10-01) | 16 chemins |
| Utilisateur de connexion à la base, sans secret | `make_url(settings.DATABASE_URL).username` | `postgres` |
| Structure de `db.json`, sans valeurs | script Node : clés et comptages | 3 utilisateurs, 1 `resetToken` non vide |
| Tests automatisés | `git ls-files \| grep -i test` | aucun |
| Diagnostic du serveur | `Get-Service`, `Get-NetTCPConnection`, essais IPv4/IPv6 | service Running, connexions refusées |
