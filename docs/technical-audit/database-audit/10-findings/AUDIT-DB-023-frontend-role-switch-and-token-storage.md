# AUDIT-DB-023 — L'interface laisse tout rôle basculer en « vue admin » ; jeton stocké dans le `localStorage`

## Sévérité
LOW

**Justification :**
- **Le serveur n'est pas affecté :** il relit le rôle en base à chaque requête,
  et refuse les actions réservées (T-B02, T-B03, T-B06).
- **Le risque se limite à la confusion :** un employé voit et manipule des
  écrans d'administration alimentés par des données fictives, et l'interface lui
  présente ses actions comme réussies.
- **Le jeton dans le `localStorage` n'est exploitable qu'en cas de XSS**, et
  aucune n'a été recherchée dans cet audit, centré sur les données.

## Catégorie
Sécurité / Interface

## Statut
OPEN · CONFIRMED

## Résumé
- Le bouton **« Switch to Admin View »** est affiché pour **tous** les rôles. Il
  remplace l'utilisateur courant de l'interface par un profil fictif
  (`ADMIN-01` « David Admin »), puis ouvre toutes les vues admin.
- Le jeton de session est stocké dans `localStorage['token']`.

## Détails techniques
- `src/components/Sidebar.tsx:154-159` : le bouton n'est conditionné par aucun
  rôle.
- `src/App.tsx:248-267` : `handleToggleRole` remplace `id`, `firstName`,
  `role`, etc.
- `src/App.tsx:215` : `localStorage.setItem('token', data.access_token)`.
- Le profil complet, rôle compris, est aussi dans `localStorage['dixpertia_user']`,
  donc modifiable à la main. **Seul l'affichage** en dépend.

## Impact métier
- Un employé « en vue admin » peut croire avoir créé une facture ou approuvé un
  congé. Rien n'est envoyé au serveur (AUDIT-DB-001).
- Le jeton est lisible par tout script injecté dans la page.

## Preuves
- Code cité ci-dessus.
- T-B02, T-B03 et T-B06 : le serveur refuse les actions admin à un employé.

## Composants concernés
`src/components/Sidebar.tsx`, `src/App.tsx`.

## Localisation
- **Code :** `Sidebar.tsx:154-159` ; `App.tsx:215`, `:248-267`.
- **Base :** —

## Cause racine
C'est un outil de démonstration du prototype, conservé en production.

## Recommandation
1. Supprimer le bouton, ou le réserver à un mode de développement explicite.
2. Ne jamais dériver un droit d'affichage du `localStorage`. Le dériver de la
   réponse du serveur, par exemple d'un `GET /api/me`.
3. À terme, envisager un cookie `HttpOnly; Secure; SameSite=Strict` pour le
   jeton.

## Correctif proposé
Retirer `onToggleRole` et le bouton associé.

## Risques du correctif
Aucun.

## Validation
Le bouton est absent pour un employé et pour la comptable.

## Effort estimé
S.

## Dépendances
Aucune.

## Findings liés
AUDIT-DB-001.
