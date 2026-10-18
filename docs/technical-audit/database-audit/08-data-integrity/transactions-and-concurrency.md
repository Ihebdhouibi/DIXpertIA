# Phase 8 — Transactions et concurrence

> 2026-10-01 · `develop` @ `34453a4` · analyse **côté code**
>
> Les scénarios de concurrence ci-dessous sont déduits du code. Leur
> reproduction par des requêtes simultanées est prévue une fois le serveur
> rétabli. Tant qu'elle n'a pas eu lieu, un scénario est `SUSPECTED`, même
> quand le mécanisme est certain.

## 1. Cadre d'exécution (faits)

| Élément | Constat | Référence |
|---|---|---|
| Endpoints | tous **synchrones** (`def`) : FastAPI les exécute dans un **pool de threads**, et des requêtes simultanées s'exécutent donc en parallèle | `main.py`, `app/routers/invoicing.py` |
| Session | une session par requête, ouverte et fermée par `get_db` | `app/core/database.py:11-17` |
| Démarcation des transactions | implicite : la transaction s'ouvre à la première requête SQL, et se termine par `db.commit()` ou par la fermeture de la session (rollback implicite) | — |
| Rollback explicite | **aucun** dans tout le code | recherche de `rollback(` |
| Verrouillage | **aucun** : ni `with_for_update`, ni `SELECT … FOR UPDATE`, ni verrou applicatif | recherche de `with_for_update`, `FOR UPDATE` |
| Niveau d'isolation | celui par défaut de PostgreSQL, `READ COMMITTED` (aucun `isolation_level` configuré) | `app/core/database.py:6` |
| Gestion des erreurs d'intégrité | **aucune** : un `IntegrityError` devient une erreur 500 | — |

Avec `READ COMMITTED` et sans verrou, tout schéma de la forme « lire, calculer,
puis écrire » est exposé aux accès concurrents. Seules les contraintes `UNIQUE`
et `PRIMARY KEY` les rattrapent, et elles le font par une erreur 500.

## 2. Analyse des opérations critiques

### T1 — Création de compte (`POST /api/users`, `main.py:224-269`)

```text
1. SELECT … WHERE email = ?            vérification d'unicité de l'e-mail
2. SELECT count(*) FROM users          calcul de l'id USR-{count+1}
3. INSERT users                        
4. COMMIT
5. send_email()                        après le commit, erreur journalisée seulement
```

| Risque | Mécanisme | Statut |
|---|---|---|
| **Collision d'id, déjà présente aujourd'hui** | les id ne sont pas contigus (`USR-001/003/005/006`) : `count()+1` = 5, soit `USR-005`, déjà pris | SUSPECTED, forte probabilité (Q-INT-006 tranchera) |
| Collision par concurrence | deux créations simultanées lisent le même `count` et obtiennent le même id : l'une échoue sur la PK | SUSPECTED |
| Doublon d'e-mail par concurrence | les deux passent l'étape 1 avant que l'une commite : le `UNIQUE` en rattrape une, par une erreur 500 et non le 400 prévu | SUSPECTED |
| Compte créé sans que l'utilisateur soit prévenu | si l'étape 5 échoue, le compte existe et le mot de passe n'est plus que dans la réponse HTTP | CONFIRMED (code) |
| Réutilisation d'un id | si un compte est un jour supprimé, `count()` diminue et un id existant est recalculé. Aucun endpoint de suppression n'existe aujourd'hui. | OBSERVATION |

### T2 — Création de facture (`POST /api/invoices`, `app/routers/invoicing.py:55-82`)

```text
1. SELECT count(*) WHERE numero LIKE 'FA-{année}-%'   numéro = count+1
2. INSERT invoices ; FLUSH
3. INSERT invoice_items × N
4. COMMIT
5. sérialisation InvoiceOut                         échec probable si statut NULL (OBS-020)
```

| Risque | Mécanisme | Statut |
|---|---|---|
| ✅ **Atomicité en-tête + lignes** | un seul `commit` : l'en-tête et ses lignes sont enregistrés ensemble ou pas du tout | CONFIRMED (code) — **point positif** |
| ✅ Montants calculés côté serveur | `_compute_totals` ignore tout montant envoyé par le client | CONFIRMED (code) — **point positif** |
| **Double numéro par concurrence** | deux créations simultanées calculent le même `FA-AAAA-NNNN` : le `UNIQUE(numero)` en rejette une, par une erreur 500 et sans nouvelle tentative | SUSPECTED |
| **Numérotation non fiable** | `count()` compte les lignes et non le plus grand numéro attribué. Toute facture `FA-` insérée hors séquence, ou supprimée, fausse le calcul et provoque collision ou trou. La numérotation n'est garantie ni continue ni croissante (ticket #38). | CONFIRMED (code) |
| **Erreur 500 après commit, puis doublon** | la facture est enregistrée, le client reçoit une erreur, la nouvelle tentative crée une 2e facture avec un nouveau numéro | SUSPECTED (OBS-020) |
| Date et année dépendant du fuseau du serveur | `date.today()` utilise l'heure locale du serveur, alors que les autres horodatages sont en UTC (`utcnow`). Autour du 1er janvier, l'année du numéro et la date d'émission peuvent diverger selon le fuseau de l'hébergement. | CONFIRMED (code) · impact `NOT VERIFIED` |

### T3 — Vente d'appareils avec une facture (`main.py:393-423`, **code mort**)

Ce code est masqué par T2, mais il documente l'intention :
`SELECT device` → `if status != 'Sold'` → `status = 'Sold'`, dans le même commit
que la facture.

- **Double vente par concurrence.** Deux factures simultanées pour le même
  appareil passent toutes deux le test : aucun verrou ni contrainte ne les en
  empêche, et aucune table ne relie les appareils aux factures. `SUSPECTED`,
  à réévaluer si le code est réactivé.
- **Appareil inexistant ignoré silencieusement.** `if dev and …` : un
  identifiant faux ne provoque aucune erreur.

### T4 — Réinitialisation du mot de passe (`main.py:271-326`)

| Risque | Mécanisme | Statut |
|---|---|---|
| Double utilisation d'un même jeton | deux requêtes simultanées passent `user.resetToken == token` avant que l'une ne remette le jeton à NULL | SUSPECTED · impact faible : c'est le même détenteur du lien |
| ✅ Nouvelle demande = ancien jeton invalidé | `resetToken` est écrasé à chaque demande | CONFIRMED (code) — **point positif** |
| Sessions conservées | les jetons de session émis avant la réinitialisation restent valides 60 min | CONFIRMED (code) |

### T5 — Décision sur un congé (`main.py:354-371`)

- **Aucune règle de transition.** Une demande déjà refusée peut être approuvée,
  et inversement. Une même demande peut être décidée plusieurs fois.
- **Aucune trace de la décision :** ni `valide_par_id` ni date.
- **Aucun verrou :** deux décideurs simultanés ne savent pas qui l'emporte.
- **En pratique, rien n'est écrit**, puisque l'attribut `status` n'est pas une
  colonne (OBS-006). Le défaut de concurrence est donc aujourd'hui masqué par un
  défaut plus grave.

Statut : CONFIRMED (code) pour l'absence de règle ; SUSPECTED pour l'effet.

### T6 — Appareils : modification et suppression (`main.py:452-482`)

| Risque | Mécanisme | Statut |
|---|---|---|
| Mise à jour perdue | `PUT` réécrit tous les champs, sans version ni comparaison : la dernière écriture écrase silencieusement l'autre | CONFIRMED (code) |
| **Collision d'id après suppression** | avec `DEV-001` à `DEV-003`, la suppression de `DEV-002` ramène `count()` à 2, donc la création suivante calcule `DEV-003`, déjà pris : erreur 500. **Les créations restent bloquées tant que le compte ne dépasse pas l'id maximal.** | CONFIRMED (logique du code) |
| Suppression d'un appareil vendu | suppression physique ; aucune FK ne la protège puisque le lien facture ↔ appareil n'existe pas | CONFIRMED (code) |
| Toutes ces routes plantent avant d'atteindre la base | `current_user['role']` (OBS-010) | SUSPECTED |

Le même défaut d'identifiant touche `team_members` (`TM-00{count+1}`) et
`leave_requests` (`LR-00{count+1}`). Ces derniers ont de plus un format
incohérent : `LR-00` suivi de 3 chiffres, soit `LR-00001`.

### T7 — Changement de rôle, désactivation, suppression d'utilisateur

**Aucun endpoint n'existe.** Ces opérations ne peuvent se faire qu'en SQL direct
ou avec `seed_users.py --admin`.

Ce script **réinitialise le mot de passe et force le rôle `admin`** de
n'importe quel compte existant dont on donne l'e-mail (`seed_users.py:65-74`).
C'est un outil d'exploitation légitime, mais il est **sans garde-fou ni trace**.
Toute personne ayant accès au serveur et au `.env` peut faire de n'importe qui
un admin. CONFIRMED (code).

### T8 — Scripts de données

| Script | Transactions | Idempotent ? |
|---|---|---|
| `migrate_data.py` | un seul commit final : tout ou rien | ❌ non : une 2e exécution provoque une violation de PK sur `users` |
| `seed_users.py` | un commit pour l'import, un pour l'admin | ✅ oui : il teste l'existence par id et par e-mail |
| `insert_invoices.py` | un commit **par client** et **par facture** | ✅ oui : il teste l'existence par nom et par numéro. Une interruption laisse un état partiel, cohérent. |

## 3. Synthèse

| | Nombre |
|---|---|
| Opérations critiques analysées | 8 |
| Opérations correctement atomiques | 1 : facture et lignes (T2) |
| Schémas « lire, calculer, écrire » sans verrou | 7 générateurs d'id ou de numéro, plus T3, T4, T5 et T6 |
| Erreurs d'intégrité transformées en 500, sans réessai | toutes |

**Cause racine commune :** les identifiants et les numéros sont générés par
l'application, à partir de `count()`, au lieu de l'être par la base (séquence ou
`IDENTITY`), et aucune erreur d'intégrité n'est traitée.

À l'échelle actuelle (quelques utilisateurs), la concurrence est **peu
probable**. En revanche, la collision après suppression, ou sur des
identifiants non contigus, se produit **sans aucune concurrence** : c'est le cas
de `USR-005` aujourd'hui. C'est ce point qui rend le défaut réel dès maintenant.
