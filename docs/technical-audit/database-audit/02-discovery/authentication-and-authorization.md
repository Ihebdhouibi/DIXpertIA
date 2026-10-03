# Authentification et autorisation

> Phase 1 — Discovery · 2026-10-01 · `develop` @ `34453a4`
>
> Ce document décrit ce que **le code fait**. Les essais réels (jeton expiré,
> jeton de réinitialisation réutilisé, accès inter-rôles, etc.) sont planifiés
> en phase 6. Tant qu'ils n'ont pas eu lieu, toute conséquence d'exécution est
> marquée `SUSPECTED`.

## 1. Authentification

### Connexion
- **Endpoint :** `POST /api/login` (`main.py:195-222`), corps JSON `{email, password}`.
- **Vérification :** `bcrypt.checkpw` sur `users.hashedPassword` (`main.py:51-52`).
- **Jeton :** JWT HS256, claims `sub` (= `users.id`), `role` et `exp` = maintenant + 60 min
  (`main.py:94-98`, `:206`).
- **Réponse :** le jeton + un objet `user` sans secret.
- **Stockage côté client :** `localStorage['token']` (`src/App.tsx:215`), plus le
  profil dans `localStorage['dixpertia_user']`.

### Ce que la connexion ne vérifie pas (CONFIRMED par lecture du code)

| Contrôle | Présent ? | Référence |
|---|---|---|
| `users.isActive` à la connexion | ❌ non | `main.py:198-206` |
| `users.isActive` à chaque requête | ❌ non | `main.py:107-114`, `app/core/deps.py:13-30` |
| `users.isVerified` | ❌ non : la colonne n'est utilisée nulle part pour autoriser | — |
| Limitation des tentatives ou verrouillage | ❌ non | — |
| Révocation de jeton ou déconnexion côté serveur | ❌ non : la déconnexion efface seulement le `localStorage` (`App.tsx:239-246`) | — |
| Invalidation des jetons existants après un changement de mot de passe | ❌ non | `main.py:303-326` |
| Type du jeton (`purpose`) | ❌ non : voir § 3 | — |

Un compte désactivé (`isActive = false`) peut donc, d'après le code, continuer à
se connecter et à appeler l'API : `SUSPECTED`, à prouver en phase 6.

### Réinitialisation du mot de passe
1. `POST /api/forgot-password` signe un JWT `{sub, exp: +1h, purpose: "reset"}`
   avec la **même** `SECRET_KEY` que les jetons de session, le stocke **en
   clair** dans `users.resetToken`, puis l'envoie par e-mail (`main.py:271-301`).
2. `POST /api/reset-password` vérifie la signature, puis que
   `users.resetToken == token`, puis la date d'expiration, avant d'écrire le
   nouveau hash (`main.py:303-326`).
3. **Aucune règle de complexité** n'est imposée au nouveau mot de passe
   (`ResetPasswordRequest.newPassword: str`, `main.py:183-185`).

La réponse est identique, que l'e-mail existe ou non : c'est correct contre
l'énumération par réponse. En revanche, le chemin « e-mail inconnu » ne calcule
aucun bcrypt, d'où une différence de temps de réponse possible (`SUSPECTED`).

### Deux piles d'authentification coexistent

| | Pile A — `main.py` | Pile B — `app/core/` |
|---|---|---|
| Hash | `bcrypt` direct | `passlib` CryptContext |
| Décodage | `decode_token` → `None` si invalide | `decode_access_token` → lève `JWTError` |
| `get_current_user` | `main.py:107` (`tokenUrl="token"`) | `app/core/deps.py:13` (`tokenUrl="/api/auth/login"`) |
| Utilisée par | endpoints de `main.py` | router `invoicing` |
| Clé | `os.getenv("SECRET_KEY", <valeur de repli>)`, valeur : `SECRET DETECTED — VALUE REDACTED` | `settings.SECRET_KEY`, même valeur de repli |

Les deux acceptent les jetons de l'autre, parce qu'elles partagent la même clé
et le même algorithme. Elles divergent sur la gestion des erreurs.

## 2. Modèle de rôles

- **Stockage :** `users.role`, une chaîne libre (`app/models/user.py:11`). Il
  n'existe ni ENUM, ni CHECK, ni table de rôles.
- **Rôles attendus :** `admin`, `employee`, `accountant` (`src/types.ts:1`,
  commentaire en `app/models/user.py:11`).
- **Rôle fantôme `rh` :** il est accepté par `require_roles("rh", "admin", "accountant")`
  (`app/routers/invoicing.py:14`) et par les routers non montés, mais n'existe
  nulle part ailleurs.
- **Création :** `POST /api/users` accepte n'importe quelle chaîne comme `role`
  (`main.py:170-174`). Un admin peut donc attribuer `rh`, ou un rôle inconnu.
- **Un seul rôle par utilisateur.** Il n'existe **aucun endpoint pour modifier
  un rôle**, ni pour désactiver ou supprimer un compte.
- **Permissions :** il n'y a **pas de notion de permission**, uniquement des
  comparaisons de chaînes de rôle, endpoint par endpoint.
- **Propriété (ownership) :** elle n'est appliquée que sur les bulletins de
  paie, dans `/api/data` (`main.py:505-509`). Aucune autre entité n'a de
  propriétaire contrôlé.

## 3. Matrice des endpoints exposés

Ce sont les routes réellement enregistrées, confirmées par `GET /openapi.json`
le 2026-10-01. Pour chaque route, la matrice distingue :
- l'**authentification** : le jeton est-il exigé ?
- le **contrôle de rôle** : quel rôle est requis ?
- le **contrôle d'objet** : vérifie-t-on que l'objet demandé appartient à
  l'appelant ?

| Méthode | Route | Défini dans | Auth | Contrôle de rôle | Contrôle d'objet | Remarque |
|---|---|---|---|---|---|---|
| POST | `/api/login` | `main.py:195` | public | — | — | normal |
| POST | `/api/forgot-password` | `main.py:271` | public | — | — | normal |
| POST | `/api/reset-password` | `main.py:303` | jeton de reset | — | — | normal |
| POST | `/api/users` | `main.py:224` | ✅ | `admin` | — | renvoie `tempPassword` en clair dans la réponse |
| GET | `/api/data` | `main.py:492` | ✅ | **aucun** | bulletins seulement | **tout rôle reçoit tous les utilisateurs, congés, factures, appareils et membres** |
| POST | `/api/leave-requests` | `main.py:335` | ❌ **aucune** | ❌ | `employeeId` fourni par l'appelant | anonyme ; plante probablement (OBS-008) |
| POST | `/api/leave-requests/{id}/approve` | `main.py:354` | ❌ **aucune** | ❌ | ❌ | **approbation anonyme** |
| POST | `/api/leave-requests/{id}/reject` | `main.py:363` | ❌ **aucune** | ❌ | ❌ | **refus anonyme** |
| POST | `/api/team-members` | `main.py:373` | ❌ **aucune** | ❌ | — | **insertion anonyme**, compatible avec le modèle |
| GET | `/api/devices` | `main.py:427` | ✅ | `current_user['role']` | — | `User` n'est pas indexable → probable 500 |
| POST | `/api/devices` | `main.py:433` | ✅ | `current_user['role']` | — | idem |
| PUT | `/api/devices/{id}` | `main.py:452` | ✅ | `current_user['role']` | — | idem |
| DELETE | `/api/devices/{id}` | `main.py:473` | ✅ | `current_user['role']` | — | idem ; suppression physique |
| GET/POST/OPTIONS | `/logs` | `main.py:485`, `:488` | ❌ | — | — | renvoie `[]` ; route déclarée deux fois |
| GET | `/api/clients` | router `invoicing.py:19` | ✅ | `rh`, `admin`, `accountant` | — | tous les clients |
| POST | `/api/clients` | router `invoicing.py:24` | ✅ | `rh`, `admin`, `accountant` | — | la comptable peut créer des clients |
| GET | `/api/invoices` | router `invoicing.py:50` | ✅ | `rh`, `admin`, `accountant` | — | aucun filtre ni pagination |
| POST | `/api/invoices` | router `invoicing.py:55` | ✅ | `rh`, `admin`, `accountant` | — | **la comptable peut créer des factures** ; masque `main.py:393` |
| GET | `/api/invoices/{invoice_id}` | router `invoicing.py:85` | ✅ | `rh`, `admin`, `accountant` | — | |
| GET | `/api/invoices/{invoice_number}/download` | router `invoicing.py:94` | ✅ | `rh`, `admin`, `accountant` | — | |

### Code d'autorisation présent mais inactif
- `main.py:393-423` : un `POST /api/invoices` réservé à l'admin. Il est
  **masqué** par la route du router, enregistrée avant lui (`main.py:40`), qui
  autorise aussi la comptable. La règle « seul l'admin crée des factures » n'est
  donc pas appliquée.
- `app/routers/auth.py`, `leaves.py`, `payroll.py` et `services.py` ne sont pas
  montés. Ils contiennent des contrôles (`require_roles("rh", "admin")` sur les
  décisions de congés, ownership sur les bulletins) qui ne s'exécutent jamais.

## 4. Autorisation côté frontend

Ce sont des contrôles **d'affichage uniquement** : ils ne protègent aucune
donnée serveur.

| Onglet | Rôles autorisés dans l'UI | Référence |
|---|---|---|
| Invoices | admin, accountant | `Sidebar.tsx:52` |
| Leave Requests | employee | `Sidebar.tsx:55` |
| Projects | admin | `Sidebar.tsx:57` |
| Payslips | employee, accountant | `Sidebar.tsx:60` |
| Team | admin, employee | `Sidebar.tsx:62` |
| Users | admin, accountant (lecture seule annoncée) | `Sidebar.tsx:64` |
| Dashboard, Notifications, Settings | tous | `Sidebar.tsx:50`, `:66-67` |

**Bouton « Switch to Admin View »** (`Sidebar.tsx:154-159`, `App.tsx:248-267`) :
- Il est **affiché pour tous les rôles**, employé et comptable compris.
- Il remplace l'utilisateur courant de l'UI par un profil fictif (`ADMIN-01`
  « David Admin », ou `EMP-102` « John Doe »), et ouvre toutes les vues admin.
- Le jeton serveur ne change pas. Les appels à l'API restent faits avec le rôle
  réel, et le serveur re-lit le rôle en base, ce qui est correct.
- **Risque réel :** les vues admin affichent les données du `localStorage`, et
  un employé peut y saisir des actions que l'UI présente comme réussies. Cela
  ajoute à la confusion décrite dans `application-data-flow.md`.

## 5. Synthèse pour les phases suivantes

Ce qui protège réellement les données aujourd'hui :
- le jeton JWT ;
- le contrôle `admin` de `POST /api/users` ;
- le `require_roles` du router `invoicing` ;
- le filtre des bulletins dans `/api/data` ;
- le filtre `_PRIVATE_COLUMNS` qui retire les hash et les jetons des réponses
  (`main.py:118-129`).

Tout le reste relève de la phase 6, avec preuves à l'appui. Voir
`discovery-observations.md`.
