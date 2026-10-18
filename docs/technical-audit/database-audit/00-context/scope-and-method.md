# Contexte, périmètre et méthode

## Pourquoi cet audit

DI Xpertia est une plateforme interne de gestion d'entreprise : employés,
comptes et accès, rôles, factures, informations administratives. Elle sert
trois profils, administrateur, employé et comptable.

La comptable doit pouvoir être notifiée des factures en attente, les approuver
ou les refuser, et les filtrer par jour, par mois et par client. L'administrateur
doit pouvoir générer des factures.

L'audit doit répondre, **preuves à l'appui**, à la question :

> « La couche données actuelle de DI Xpertia est-elle correctement conçue,
> cohérente avec le métier, sécurisée, intègre et suffisamment robuste pour
> continuer le développement de la plateforme ? »

## Périmètre

La chaîne complète :

**Métier et fonctionnalités → modèles applicatifs → ORM → migrations → schéma →
tables → colonnes → PK/FK → relations → contraintes → index → données → requêtes
→ accès → permissions → sécurité → cohérence applicative**

- **Code :** branche `develop` à `34453a4` (2026-09-23), soit le backend
  (`main.py`, `app/`, scripts racine) et le frontend (`src/`, en tant que
  consommateur de données).
- **Base :** l'instance PostgreSQL 17 **locale** (`localhost:5432/dixpertia`),
  créée par `tables.py` le 2026-10-01. **Aucune base de production n'est
  accessible ni auditée.** Les constats sur les données réelles de production
  sont donc hors de portée et seront marqués `NOT VERIFIED`.

## Règles d'intervention

1. **Aucune modification** du code, du schéma ou des données pendant l'audit.
   Les corrections sont décrites dans les tickets.
2. Toutes les requêtes passent par `01-requests/scripts/run_readonly.py`, qui
   force `default_transaction_read_only = on` au niveau du serveur.
3. Un test qui **écrit**, même en base locale, ne sera lancé qu'avec accord
   explicite. C'est le cas de la création d'un compte de test, d'un appel
   d'insertion ou d'une tentative de création qui échoue.
4. **Aucun secret** n'est recopié. Mots de passe, hash, jetons et clés
   apparaissent sous la forme `SECRET DETECTED — VALUE REDACTED`.
5. Chaque constat distingue **Fait → Observation → Impact → Recommandation**.

## Statuts utilisés

| Statut | Usage |
|---|---|
| `OBSERVATION` | constat neutre, impact à qualifier |
| `SUSPECTED` | conséquence probable d'après le code, pas encore prouvée |
| `CONFIRMED` | prouvé par une lecture de code référencée, une requête, une réponse HTTP ou un log |
| `NOT VERIFIED` | vérification impossible, avec la raison indiquée |
| `UNKNOWN / NEEDS VERIFICATION` | information introuvable dans le dépôt |

## Échelle de sévérité

La sévérité est justifiée, finding par finding, sur ces critères : impact,
exploitabilité, portée, probabilité, risque de corruption de données, risque de
sécurité et risque métier.

| Niveau | Critère de référence |
|---|---|
| `CRITICAL` | Exploitable sans authentification ou par n'importe quel rôle, avec un impact direct sur la confidentialité ou l'intégrité de données sensibles, ou une perte de données. |
| `HIGH` | Exploitable par un utilisateur authentifié au-delà de ses droits, ou corruption de données probable dans un usage normal, ou fonctionnalité métier centrale inopérante. |
| `MEDIUM` | Risque réel mais conditionnel (configuration, concurrence, scénario précis), ou dette qui rend une évolution coûteuse. |
| `LOW` | Faiblesse limitée, mauvaise pratique sans exploitation directe. |
| `INFO` | Constat utile, sans risque propre. |

## Phases

| # | Phase | Dossier principal |
|---|---|---|
| 1 | Discovery | `02-discovery/` |
| 2 | Inventaire de la base | `03-schema/` |
| 3 | Audit des modèles | `04-models/` |
| 4 | Audit des relations | `05-relations/` |
| 5 | Intégrité des données | `08-data-integrity/` |
| 6 | Sécurité et accès | `06-security/` |
| 7 | Performance | `07-performance/` |
| 8 | Transactions et concurrence | `08-data-integrity/` |
| 9 | Règles métier | `09-business-rules/` |
| 10 | Consolidation des findings | `10-findings/` |
| 11 | Preuves | `11-evidence/` |
| 12 | Tickets | `13-tickets/` |
| 13 | Rapport final | `14-final-report/` |

Les transactions et la concurrence (§ 14 de la mission) sont rangées avec
l'intégrité, faute de dossier dédié dans la structure demandée.
