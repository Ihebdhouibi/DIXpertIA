# Audit de la couche données — DI Xpertia

> Dossier technique de référence de l'audit de bout en bout de la base de
> données et du modèle de données, versionné dans le dépôt.

## Pourquoi cet audit existe

Avant de poursuivre le développement, notamment le circuit de factures de la
comptable et la refonte v2, il fallait savoir si la couche données est
correctement conçue, cohérente avec le métier, sécurisée, intègre et robuste.
La réponse devait reposer sur des preuves, pas sur une impression.

**Réponse (rapport final) : non, pas en l'état. Elle est réparable, et le
moment est favorable :** les tables sont quasi vides, et l'interface n'utilise
pas encore l'API, donc les défauts n'ont pas produit de dégâts.

👉 **Lire d'abord :** [`14-final-report/database-audit-final-report.md`](14-final-report/database-audit-final-report.md)

## État

| | |
|---|---|
| **Statut** | ✅ **Audit terminé** (2026-10-02) |
| **Code audité** | `develop` @ `34453a4` |
| **Base auditée** | PostgreSQL 17.11 local, `dixpertia`. Aucune base de production n'était accessible. |
| **Preuves** | 69 requêtes SQL en lecture seule · 30 sondes de contraintes (transaction annulée) · 20 tests d'API · log du backend masqué |
| **Findings** | **24**, toutes CONFIRMED |
| **Tickets** | **14 + 1 parent**, brouillons en anglais, **non encore publiés** sur GitHub |

### Répartition par sévérité

| CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|
| **1** | **10** | **5** | **8** | 0 |

## Avancement des phases

| # | Phase | État | Livrable |
|---|---|---|---|
| 1 | Discovery | ✅ | `02-discovery/` |
| 2 | Inventaire de la base | ✅ | `11-evidence/schema/`, `02-discovery/database-overview.md` |
| 3 | Modèles ORM | ✅ | `04-models/` |
| 4 | Relations et ERD | ✅ | `05-relations/` |
| 5 | Intégrité des données | ✅ | `08-data-integrity/data-integrity-results.md` |
| 6 | Sécurité et accès | ✅ | `06-security/` |
| 7 | Performance | ✅ | `07-performance/` |
| 8 | Transactions et concurrence | ✅ (analyse du code) | `08-data-integrity/transactions-and-concurrency.md` |
| 9 | Règles métier | ✅ (36 règles) | `09-business-rules/` |
| 10 | Findings | ✅ (24) | `10-findings/` |
| 11 | Preuves | ✅ | `11-evidence/` |
| 12 | Recommandations | ✅ | `12-recommendations/remediation-plan.md` |
| 13 | Tickets | ✅ (rédigés, non encore publiés) | `13-tickets/` |
| 14 | Rapport final | ✅ | `14-final-report/` |

## Les findings les plus graves

| ID | Sévérité | Finding |
|---|---|---|
| AUDIT-DB-002 | **CRITICAL** | Écritures sans authentification : membres d'équipe, création et décision de congés |
| AUDIT-DB-003 | HIGH | Un employé lit tous les comptes, les factures et les congés via `/api/data` |
| AUDIT-DB-004 | HIGH | Un compte désactivé ou « supprimé » garde l'accès |
| AUDIT-DB-006 | HIGH | L'application est superutilisateur PostgreSQL |
| AUDIT-DB-007 | HIGH | Clé JWT de repli et mot de passe de la base dans le dépôt |
| AUDIT-DB-011 | HIGH | Le circuit comptable (approbation, notifications, filtres) n'existe pas |
| AUDIT-DB-012 | HIGH | La création de compte échoue systématiquement (collision d'identifiant) |
| AUDIT-DB-014 | HIGH | La base accepte 26 types de données métier invalides sur 26 testés |

La liste complète est dans [`10-findings/README.md`](10-findings/README.md).

## Prochaines étapes recommandées

1. **Immédiatement, hors code :** changer le mot de passe du rôle `postgres`
   sur tout environnement qui utiliserait la valeur du dépôt, ainsi que ceux des
   3 comptes présents dans `db.json`.
2. **Phase 0 :** TICKET-DB-002 et TICKET-DB-004.
3. **Décisions métier** listées dans `12-recommendations/remediation-plan.md`,
   dont l'issue #37.
4. Publier les tickets sur GitHub après relecture, en rattachant DB-005, 006 et
   004 aux issues #37, #38/#39 et #43.

## Navigation

| Dossier | Contenu |
|---|---|
| `00-context/` | périmètre et méthode, **journal d'audit** |
| `01-requests/` | toutes les requêtes SQL et les scripts (lecture seule, sondage, tests d'API), avec leur objectif |
| `02-discovery/` | stack, structure, vue d'ensemble de la base, flux de données, authentification et autorisation, **registre des 41 observations avec leurs verdicts** |
| `03-schema/` | *(non utilisé : l'inventaire est dans `11-evidence/schema/` et `02-discovery/database-overview.md`)* |
| `04-models/` | correspondance frontend ↔ API ↔ ORM ; ORM ↔ base ↔ migrations |
| `05-relations/` | ERD et analyse des relations |
| `06-security/` | analyse statique ; tests à l'exécution |
| `07-performance/` | analyse statique ; plans d'exécution |
| `08-data-integrity/` | résultats d'intégrité ; transactions et concurrence |
| `09-business-rules/` | matrice des 36 règles métier |
| `10-findings/` | 24 findings `AUDIT-DB-XXX` |
| `11-evidence/` | preuves reproductibles (résultats SQL, plans, sondes, tests d'API, log masqué) |
| `12-recommendations/` | plan de remédiation |
| `13-tickets/` | 14 tickets + ticket parent |
| `14-final-report/` | rapport final |

## Ce qui reste hors de portée

- Toute **base de production** : schéma et données `NOT VERIFIED`. Il faut y
  rejouer les requêtes et le sondage.
- La **configuration de déploiement**, notamment la présence de `SECRET_KEY`.
- La reproduction **effective** des scénarios de concurrence.
- La sécurité du frontend au-delà des données (XSS, dépendances npm).

## Données laissées par l'audit en base locale

Toutes sont marquées `AUDIT-TEST`. **Rien n'a été supprimé** ; le nettoyage
demande un accord explicite.
- 3 comptes : `USR-008`, `009` et `010` ;
- 1 client ;
- 2 factures (`FA-2026-0001` et `0002`, statut NULL) et leurs lignes ;
- 1 membre d'équipe (`TM-00001`) ;
- 1 demande de congé (id 7).
