# Phase 3 — Modèles ORM ↔ schéma réel ↔ migrations

> 2026-10-02 · base locale `dixpertia`
>
> **Preuves :** `11-evidence/schema/01-discovery-overview.results.md` et
> `02-schema-inventory.results.md`.

## 1. ORM ↔ schéma réel

La base locale a été créée par `create_all()` à partir des modèles actuels, le
2026-10-01. On s'attend donc à une correspondance exacte, et c'est ce qui est
observé.

| Contrôle | Résultat |
|---|---|
| Modèle sans table | aucun : 9 modèles, 9 tables (Q-DISC-005) |
| Table sans modèle | aucune |
| Colonne présente dans un seul des deux | aucune : 71 colonnes comparées (Q-SCH-001) |
| Types | conformes ; `devices.price` est bien `double precision` (Q-SCH-011) |
| Nullabilité | conforme aux modèles, y compris les colonnes nullables à tort (`leave_requests.employee_id`, `invoices.statut`, `cree_par_id`, `montant_*`, `users.role`, `hashedPassword`…) |
| FK | 6 en base, 6 dans les modèles, toutes en `NO ACTION` (Q-SCH-004) |
| Valeurs par défaut | **divergence de nature** : voir ci-dessous |
| Index | 9 index redondants créés par `index=True` sur les PK (Q-SCH-006) |
| ENUM | noms des membres stockés (Q-SCH-009) |

### La divergence qui compte : les valeurs par défaut

Les valeurs par défaut des modèles sont **côté Python**. La base n'en connaît
que deux : `now()` sur `payslips.date_emission` et sur
`leave_requests.created_at`.

| Colonne | Défaut dans le modèle | Défaut en base |
|---|---|---|
| `users.isActive` | `True` | **aucun** → NULL (sonde P-24) |
| `users.isVerified` | `False` | aucun |
| `users.createdAt`, `devices.createdAt` | `datetime.utcnow` | aucun |
| `devices.status` | `"Available"` | aucun |
| `invoice_items.quantite` | `1` | aucun |
| `invoice_items.taux_tva` | `19` | aucun |
| `leave_requests.type_conge` | `PAYE` | aucun |
| `leave_requests.statut` | `EN_ATTENTE` | aucun |
| `services.ordre_affichage`, `actif`, `description` | `0`, `True`, `""` | aucun |
| `clients.email`, `telephone`, `adresse` | `""` | aucun |

**Conséquence :** toute écriture qui ne passe pas par l'ORM produit des NULL.
C'est le cas d'un script SQL, d'un import, de pgAdmin ou d'un autre service. Un
`isActive` NULL n'est ni actif ni inactif ; il reste sans effet tant
qu'`isActive` n'est vérifié nulle part (OBS-011), mais deviendra un piège le
jour où il le sera.

### Colonnes à guillemets

**14 colonnes** ont des majuscules (Q-SCH-002) : 9 dans `users`, 3 dans
`team_members` et 2 dans `devices`. Tout SQL écrit à la main doit les
entourer de guillemets (`"isActive"`). Un oubli produit une erreur « column
does not exist », ou pire, cible une autre colonne si une version en
minuscules existe un jour.

## 2. Migrations ↔ base

| Contrôle | Résultat |
|---|---|
| Fichiers de migration | **0** (`alembic/versions/` vide) |
| Table `alembic_version` | **absente** (Q-DISC-009) |
| Historique du schéma | **aucun** |

**Conséquence, confirmée :** il est impossible de savoir quel schéma tourne sur
un environnement donné, de le faire évoluer sans perte, ou de reproduire un
état antérieur.

`create_all()` ne modifie jamais une table existante. Toute base créée **avant**
la dernière modification des modèles, par exemple une base de production si
elle existe, a donc pu garder un schéma différent de celui-ci. Ce point est `NOT VERIFIED` :
aucune base de production n'est accessible.

## 3. Comparaison avec la couche API

La comparaison champ par champ avec l'API et le frontend est dans
`orm-api-frontend-mapping.md`. Les tests d'exécution ont confirmé les
divergences les plus graves :

| Divergence | Preuve à l'exécution |
|---|---|
| L'API crée un `LeaveRequest` avec des champs camelCase inexistants | T-A03 : `TypeError: 'employeeId' is an invalid keyword argument for LeaveRequest` |
| L'API écrit `leave.status`, alors que la colonne est `statut` | T-B09 : réponse de succès, statut inchangé en base |
| Le schéma de sortie `InvoiceOut.statut` est obligatoire, alors que la colonne est nullable et jamais remplie | T-B05 : `ResponseValidationError … statut … input: None` |
| L'API indexe un objet ORM comme un dictionnaire | T-A05 : `TypeError: 'User' object is not subscriptable` |
