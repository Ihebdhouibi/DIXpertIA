# Phase 5 — Intégrité des données : résultats

> 2026-10-02 · base locale `dixpertia`
>
> **Preuves :**
> - `11-evidence/data-integrity/03-data-integrity.results.md` (Q-INT-001 à 020) ;
> - `11-evidence/data-integrity/constraint-probe.results.md` (30 sondes, en transaction annulée).

## 1. Ce que l'on peut et ne peut pas conclure

Au moment de l'exécution de Q-INT, la base contenait **4 utilisateurs** et 8
tables **vides** (Q-INT-001). L'absence d'anomalie dans les données **ne
prouve donc rien** sur la qualité du modèle.

C'est pourquoi l'audit a mesuré **ce que la base empêche**, plutôt que ce
qu'elle contient : c'est le rôle du sondage des contraintes. L'audit des
données réelles de production reste `NOT VERIFIED`, faute d'accès à une
telle base.

## 2. Données existantes (Q-INT)

| Requête | Résultat | Lecture |
|---|---|---|
| Q-INT-002 — rôles | `admin` : 3, `accountant` : 1 ; aucun rôle inattendu | sain |
| Q-INT-003 — attributs obligatoires manquants | 0 partout | sain, mais aucune contrainte ne l'impose (sonde P-22) |
| Q-INT-004 — doublons d'e-mail, toutes casses confondues | 0 | sain, mais la base les accepterait (P-23) |
| Q-INT-005 — format des identifiants | `USR-001, 003, 005, 006`, tous bien formés, **non contigus** | cause d'OBS-021 |
| **Q-INT-006 — prochain id généré par l'API** | **`USR-005`, `already_taken = true`** | 🔴 **preuve, au niveau des données, qu'OBS-021 se produit dans l'état naturel de la base**, confirmée à l'exécution par T-A07 |
| Q-INT-007 — jetons de réinitialisation stockés | 0. `seed_users.py` n'importe pas le `resetToken` présent dans `db.json` : comportement correct | sain |
| Q-INT-008 — `isActive` / `isVerified` | 4 actifs, dont 2 non vérifiés | `isVerified` n'a aucun effet (R-USR, `04-models/`) |
| Q-INT-009 — correspondance `team_members` ↔ `users` | 0 / 0 | tables vides : non concluant |
| Q-INT-010 — orphelins sur FK | 0 partout | attendu : les 6 FK existent bien (Q-SCH-004) |
| Q-INT-011 à 020 | 0 ligne ou 0 partout | tables vides : **non concluant** |

## 3. Ce que la base accepte (sondage des contraintes)

**26 tentatives d'écriture invalides sur 30 ont été acceptées.** Les 4 refus
correspondent exactement aux contraintes qui existent. Il restait **0 ligne**
après le rollback, ce qui a été vérifié.

### Règles métier non garanties par la base

| Domaine | Sondes acceptées | Exemples de données impossibles que la base enregistre |
|---|---|---|
| **Factures** | P-01 à P-07 | montant de **−500** ; échéance en **2020** pour une émission en **2026** ; TTC (**1**) inférieur au HT (**1000**) ; facture **sans statut** ; **sans montant** ; **sans auteur** ; en-tête de 100 alors que les lignes totalisent 2 997 |
| **Lignes de facture** | P-08 à P-11 | quantité de **−4** ; TVA de **99,99 %** ; TVA de **−19 %** ; prix unitaire de **−10** |
| **Congés** | P-12 à P-16 | demande **sans employé** ; **fin avant le début** ; **auto-validation** (`valide_par_id = employee_id`) ; congé **approuvé sans valideur** ; deux congés **qui se chevauchent** |
| **Paie** | P-17, P-18, P-20 | net (**5 000**) supérieur au brut (**1 000**) ; montants **négatifs** ; **deux bulletins pour le même mois**, le 1er et le 15 juin |
| **Comptes** | P-21 à P-24 | rôle **`superadmin`** ; compte **sans rôle ni mot de passe** ; **`PROBE@`** à côté de **`probe@`** ; `isActive` **NULL** quand on omet la valeur |
| **Inventaire** | P-25, P-26 | deux appareils avec le **même numéro de série** ; prix de **−99,99** et statut **« Volé »** |
| **Clients** | P-27 | **« AUDIT-PROBE client »** et **« audit-probe CLIENT »** coexistent |

### Contraintes qui fonctionnent

| Sonde | Contrainte | Résultat |
|---|---|---|
| P-19 | `uq_employee_periode` | ✅ rejet de deux bulletins à la **même date** |
| P-28 | FK `invoice_items.invoice_id` | ✅ rejet de la suppression SQL directe d'une facture qui a des lignes |
| P-29 | FK `payslips.employee_id` (et autres FK vers `users`) | ✅ rejet de la suppression d'un utilisateur référencé |
| P-30 | FK `invoices.client_id` | ✅ rejet d'une facture vers un client inexistant |

### Constat nouveau : la contrainte d'unicité de la paie ne protège pas le mois

`UNIQUE (employee_id, periode)` porte sur une **date** (`periode DATE`). Elle
empêche deux bulletins le **même jour**, mais pas deux bulletins le **même
mois** (P-20). Or un bulletin représente un mois.

Les solutions possibles :
- une contrainte `CHECK (extract(day FROM periode) = 1)` ;
- une unicité sur `date_trunc('month', periode)` ;
- ou une représentation de la période par un couple `(annee, mois)`.

## 4. Vérification du stockage des ENUM

- La base stocke les **noms** des membres : `BROUILLON`, `EN_ATTENTE`, `PAYE`…
  (Q-SCH-009). C'est **CONFIRMED**.
- SQLAlchemy accepte indifféremment le nom (`BROUILLON`) ou la valeur
  (`brouillon`), et envoie toujours le nom à la base. **L'hypothèse d'un échec
  de `insert_invoices.py` est donc REFUTED.**
- Reste une **OBSERVATION** : deux vocabulaires coexistent. Ce sont les
  majuscules pour la base et les outils SQL, et les minuscules pour l'API.

## 5. Effet de bord à connaître

Les séquences PostgreSQL ne sont pas annulées par un rollback : c'est le
comportement normal du SGBD. Le sondage a donc consommé des valeurs.
- La première facture réellement créée (T-B05) a l'**id 8**.
- Le premier client a l'**id 3**.

Ces trous ne concernent que les clés techniques, jamais le **numéro** de
facture, qui est la référence légale. C'est un rappel utile : **les clés
techniques ne doivent jamais servir de numérotation métier**.

## 6. Bilan

| | |
|---|---|
| Anomalies dans les données existantes | **1**, la collision d'identifiant de Q-INT-006, prouvée à l'exécution |
| Règles métier testées contre le schéma | 26, plus 4 contrôles |
| **Règles non garanties par la base** | **26 sur 26** |
| Contraintes existantes et efficaces | 4 sur 4 testées : 1 unicité et 3 clés étrangères |

**La base garantit l'intégrité référentielle (les FK), et rien d'autre.**
Toute règle métier (montants, dates, statuts, rôles, unicités métier) repose
entièrement sur l'application. Or la Phase 9 montre que l'application ne les
applique pas non plus.
