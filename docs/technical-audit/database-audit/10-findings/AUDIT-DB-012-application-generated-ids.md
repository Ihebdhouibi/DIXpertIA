# AUDIT-DB-012 — Identifiants et numéros générés par `count() + 1` : la création de compte est cassée

## Sévérité
HIGH

**Justification :**
- **Impact :**
  - **la création de compte par l'admin échoue à 100 %** dans l'état actuel de
    la base, ce qui rend inopérante une fonction centrale ;
  - la numérotation des factures, qui est la référence légale, n'est garantie
    ni continue ni robuste.
- **Probabilité :** certaine aujourd'hui pour les comptes. Toute suppression,
  ou tout id non contigu, reproduit la collision **sans aucune concurrence**.
- **Critère HIGH rempli :** une fonction centrale est inopérante, et une
  corruption est probable en usage normal.

## Catégorie
Intégrité des données / Concurrence

## Statut
OPEN · CONFIRMED

## Résumé
Les identifiants métier (`USR-NNN`, `TM-NNN`, `DEV-NNN`, `LR-NNNNN`) et les
numéros de facture (`FA-AAAA-NNNN`) sont calculés par l'application à partir
de `count(*) + 1`.

Dès que les identifiants ne sont pas contigus, la valeur calculée **existe
déjà**. C'est le cas aujourd'hui : `USR-001, 003, 005, 006`.

## Détails techniques

| Générateur | Code | Défaut |
|---|---|---|
| `USR-{count+1:03d}` | `main.py:235` | **collision prouvée** (T-A07 : `UniqueViolation users_pkey`) |
| `TM-00{count+1:03d}` | `main.py:377` | idem après une suppression ; format incohérent (`TM-00001`, alors que les autres sont sur 3 chiffres) |
| `LR-00{count+1:03d}` | `main.py:337` | idem ; route cassée par ailleurs |
| `DEV-{count+1:03d}` | `main.py:437` | **une suppression bloque les créations** jusqu'à ce que le compte dépasse l'id maximal |
| `INV-2024-00{count+1:03d}` | `main.py:401` (code mort) et le frontend | année codée en dur à **2024** |
| `FA-{année}-{count+1:04d}` | `invoicing.py:35-38` | compte les lignes au lieu de lire le dernier numéro ; `LIKE` non indexé (Q-PERF-017) ; année calculée en heure locale (`date.today()`) |

Il n'existe aucune gestion d'`IntegrityError` : toutes les collisions
deviennent des erreurs 500, avec fuite de paramètres dans les logs
(AUDIT-DB-008).

`seed_users.py:85-95` connaît précisément ce piège et le contourne, en prenant
le maximum au lieu du compte. `main.py` ne le fait pas.

## Impact métier
- **L'admin ne peut créer aucun compte** pour un nouveau salarié.
- **La numérotation des factures**, que la réglementation exige unique et
  chronologique, et sans trou dans la plupart des cadres fiscaux (ticket #38),
  repose sur un comptage fragile :
  - une facture supprimée, ou importée hors séquence, provoque une collision ou
    un trou ;
  - deux créations simultanées obtiennent le même numéro (`SUSPECTED`, la
    concurrence n'a pas été reproduite).

## Preuves
- **Q-INT-006 :** l'état naturel de la base génère `USR-005`, avec
  `already_taken = true`.
- **T-A07 :** `POST /api/users` en admin → **500**. Log :
  `UniqueViolation … users_pkey`.
- **Q-PERF-017 :** l'index sur `numero` n'est pas utilisable pour le `LIKE`.
- Analyse : `08-data-integrity/transactions-and-concurrency.md`, T1, T2 et T6.

## Composants concernés
`main.py`, `app/routers/invoicing.py`, tables `users`, `team_members`,
`devices`, `leave_requests` et `invoices`.

## Localisation
- **Code :** `main.py:235`, `:337`, `:377`, `:401`, `:437` ;
  `app/routers/invoicing.py:35-38`.
- **Base :** clés primaires VARCHAR sans valeur par défaut (Q-SCH-001) ;
  `invoices.numero`.

## Cause racine
Les identifiants sont générés par l'application, sans séquence côté base et
sans traitement des conflits.

## Recommandation
1. **Clés techniques :** les laisser à la base (`IDENTITY` ou séquence). Si un
   identifiant lisible est souhaité (`USR-005`), le **dériver** de la séquence,
   sans jamais le recompter.
2. **Numéro de facture :**
   - un **compteur par année** dans une table dédiée
     (`invoice_counters(year PK, last_value)`) ;
   - incrémenté par `UPDATE … SET last_value = last_value + 1 RETURNING`, dans
     la même transaction que l'insertion. Le verrou de ligne sérialise alors les
     créations concurrentes ;
   - **attribué à l'émission**, et non à la création du brouillon, si le métier
     exige l'absence de trou.
3. Traiter `IntegrityError` : renvoyer 409, et réessayer si c'est pertinent.

## Correctif proposé
```sql
CREATE SEQUENCE users_seq;
SELECT setval('users_seq', (SELECT max(substring(id from 5)::int) FROM users WHERE id ~ '^USR-\d+$'));
-- application : id = 'USR-' || lpad(nextval('users_seq')::text, 3, '0')

CREATE TABLE invoice_counters (year int PRIMARY KEY, last_value int NOT NULL DEFAULT 0);
-- à l'émission :
-- UPDATE invoice_counters SET last_value = last_value + 1 WHERE year = $1 RETURNING last_value;
```

## Risques du correctif
- La renumérotation des identifiants existants est **à proscrire** : ils sont
  référencés par les FK, et peut-être imprimés. On ne fait que **reprendre**
  la séquence au maximum existant.
- La date d'émission et l'année du compteur doivent utiliser **le même
  fuseau**, à définir explicitement.

## Validation
- Rejouer T-A07 : **201**, avec `USR-011` (après les comptes `AUDIT-TEST`).
- Supprimer un appareil, puis en créer un : pas de collision.
- 20 créations de factures simultanées : 20 numéros distincts et consécutifs.

## Effort estimé
M.

## Dépendances
AUDIT-DB-015 (migrations).

## Findings liés
AUDIT-DB-008, AUDIT-DB-010, AUDIT-DB-018 (index de `numero`).
