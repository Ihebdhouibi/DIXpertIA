# Findings

> 2026-10-02 · 24 findings, toutes **CONFIRMED** par une preuve reproductible
> (requête SQL, test HTTP, sonde de contraintes, log ou référence de code).
>
> Échelle de sévérité et critères : `00-context/scope-and-method.md`. Chaque
> fiche justifie sa sévérité.

## Répartition

| CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|
| **1** | **10** | **5** | **8** | 0 |

## Liste

| ID | Sévérité | Catégorie | Finding | Statut | Effort |
|---|---|---|---|---|---|
| [AUDIT-DB-002](AUDIT-DB-002-unauthenticated-write-endpoints.md) | **CRITICAL** | Sécurité | Endpoints d'écriture accessibles sans authentification (congés, équipe) | OPEN | S |
| [AUDIT-DB-001](AUDIT-DB-001-database-not-system-of-record.md) | HIGH | Architecture | La base n'est pas la source de vérité : les données métier vivent dans le navigateur | OPEN | XL |
| [AUDIT-DB-003](AUDIT-DB-003-api-data-overexposure.md) | HIGH | Sécurité | `/api/data` expose comptes, factures et congés à tout utilisateur connecté | OPEN | M |
| [AUDIT-DB-004](AUDIT-DB-004-ineffective-access-revocation.md) | HIGH | Sécurité | Révocation d'accès inopérante : un compte désactivé ou « supprimé » garde l'accès | OPEN | M |
| [AUDIT-DB-006](AUDIT-DB-006-app-runs-as-superuser.md) | HIGH | Sécurité | L'application se connecte en superutilisateur PostgreSQL (`bypassrls`) | OPEN | S |
| [AUDIT-DB-007](AUDIT-DB-007-secrets-in-repository.md) | HIGH | Sécurité | Secrets dans le dépôt : clé JWT de repli, mot de passe de la base, hash de comptes réels | OPEN | S–M |
| [AUDIT-DB-010](AUDIT-DB-010-invoice-creation-defects.md) | HIGH | Intégrité / Métier | Création de facture : la comptable peut créer, statut NULL, 500 après commit d'où des doublons | OPEN | S–M |
| [AUDIT-DB-011](AUDIT-DB-011-accounting-workflow-missing.md) | HIGH | Métier | Circuit comptable absent : ni approbation, ni notification, ni filtres | OPEN | XL |
| [AUDIT-DB-012](AUDIT-DB-012-application-generated-ids.md) | HIGH | Intégrité | Identifiants par `count()+1` : la création de compte est cassée ; numérotation fragile | OPEN | M |
| [AUDIT-DB-013](AUDIT-DB-013-split-data-model-and-dead-code.md) | HIGH | Architecture | Modèle scindé API ↔ ORM : des routes plantent, d'autres écrivent dans le vide ; code mort | OPEN | L |
| [AUDIT-DB-014](AUDIT-DB-014-no-business-integrity-constraints.md) | HIGH | Intégrité | Aucune contrainte métier : 26 types de données invalides acceptés | OPEN | M |
| [AUDIT-DB-005](AUDIT-DB-005-reset-token-weaknesses.md) | MEDIUM | Sécurité | Jeton de réinitialisation accepté comme jeton de session, et stocké en clair | OPEN | S |
| [AUDIT-DB-008](AUDIT-DB-008-sensitive-data-in-logs.md) | MEDIUM | Sécurité | Données sensibles dans les logs : hash et e-mail, mot de passe de la base | OPEN | S |
| [AUDIT-DB-015](AUDIT-DB-015-no-schema-migrations.md) | MEDIUM | Architecture | Aucune migration : schéma non versionné (**prérequis de la remédiation**) | OPEN | S |
| [AUDIT-DB-016](AUDIT-DB-016-missing-entities-and-relations.md) | MEDIUM | Modèle | Entités et relations manquantes : fiche employé, facture ↔ appareil, FK nullables | OPEN | L |
| [AUDIT-DB-017](AUDIT-DB-017-no-audit-trail.md) | MEDIUM | Conformité | Aucune traçabilité : ni journal d'audit, ni auteur des décisions | OPEN | M |
| [AUDIT-DB-009](AUDIT-DB-009-account-enumeration-timing.md) | LOW | Sécurité | Énumération des comptes par le temps de réponse (24 ms contre 292 ms) | OPEN | S |
| [AUDIT-DB-018](AUDIT-DB-018-indexing-and-query-patterns.md) | LOW | Performance | Index manquants ou redondants, lectures intégrales, N+1 | OPEN | S |
| [AUDIT-DB-019](AUDIT-DB-019-roles-and-value-representation.md) | LOW | Modèle | Rôles non modélisés (`rh` fantôme), argent en flottant, temps hétérogène, 3 vocabulaires d'ENUM | OPEN | M |
| [AUDIT-DB-020](AUDIT-DB-020-exclusion-list-serialization.md) | LOW | Sécurité | Sérialisation par liste d'exclusion : nouvelles colonnes exposées par défaut | OPEN | S |
| [AUDIT-DB-021](AUDIT-DB-021-database-server-hardening.md) | LOW | Exploitation | Serveur PostgreSQL : ni journalisation des accès, ni délais de garde | OPEN | S |
| [AUDIT-DB-022](AUDIT-DB-022-operations-and-quality-gaps.md) | LOW | Maintenabilité | Aucun test, `Dockerfile` cassé, `.env.example` et documentation obsolètes | OPEN | M |
| [AUDIT-DB-023](AUDIT-DB-023-frontend-role-switch-and-token-storage.md) | LOW | Interface | Bascule « vue admin » offerte à tous ; jeton dans le `localStorage` | OPEN | S |
| [AUDIT-DB-024](AUDIT-DB-024-account-creation-credential-handling.md) | LOW | Sécurité | Mot de passe provisoire dans la réponse ; e-mail envoyé après le commit | OPEN | M |

Effort : S < ½ jour · M ½ à 2 jours · L 2 à 5 jours · XL > 5 jours.

## Correspondance avec les observations

| Finding | Observations |
|---|---|
| 001 | OBS-001 |
| 002 | OBS-006, 007, 008 |
| 003 | OBS-009 |
| 004 | OBS-011 ; R-USR-02, R-USR-03 |
| 005 | OBS-012, 013 |
| 006 | OBS-016 |
| 007 | OBS-014, 015 |
| 008 | OBS-017, 018 (logs), 035 |
| 009 | OBS-018 (temps de réponse) |
| 010 | OBS-020 ; R-FAC-01 |
| 011 | OBS-005 ; R-FAC-02 à 04, R-FAC-08 |
| 012 | OBS-021, 022, 029 |
| 013 | OBS-002, 004, 010, 028 |
| 014 | OBS-019 (partie contraintes), 023, 036, 039 |
| 015 | OBS-003 |
| 016 | OBS-025, 026 ; relations R2, R4, R6, M1 à M3 |
| 017 | relations R3, M4 ; OBS-040 (partie journalisation) |
| 018 | OBS-030, 037, 038 |
| 019 | OBS-019 (partie modèle), 024, 027, 041 |
| 020 | `security-static-analysis.md` § 2 |
| 021 | OBS-040 |
| 022 | OBS-031, 032 |
| 023 | OBS-033 |
| 024 | OBS-034 |

## Ce qui n'a pas été retenu comme finding

| Élément | Raison |
|---|---|
| Risque d'injection SQL | aucun SQL brut dans le code : point **positif** |
| Hachage des mots de passe | bcrypt, coût 12 : point **positif** |
| Rôle relu en base à chaque requête | ignore le claim `role` du jeton : point **positif** |
| Montants de facture calculés côté serveur, en-tête et lignes en un seul commit | point **positif** |
| Contrôles du router `invoicing` (403 pour un employé) | efficaces : T-B02, T-B03, T-B06 |
| Trous dans les séquences après le sondage annulé | comportement normal de PostgreSQL, sans effet sur la numérotation métier |
| Hypothèse d'échec d'`insert_invoices.py` | **REFUTED** |
