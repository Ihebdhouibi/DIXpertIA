# Phase 9 — Matrice des règles métier

> 2026-10-01 · `develop` @ `34453a4` · analyse **côté code**
>
> **Source des règles attendues :**
> - la description du produit faite par Abir le 2026-09-15 ;
> - les tickets fermés qui ont arbitré des règles (#10, #12, #47) ;
> - les commentaires du code qui en citent.
>
> Une règle « attendue » qui ne vient d'aucune de ces sources est marquée
> `UNKNOWN / NEEDS VERIFICATION` : elle doit être confirmée par le métier.

## Légende

Chaque règle est évaluée dans trois couches :
- **UI** : ce que l'interface autorise ou empêche.
- **API** : ce que le serveur applique.
- **Base** : ce que la base garantit.

| Symbole | Sens |
|---|---|
| ✅ | appliqué correctement |
| ⚠️ | appliqué partiellement, ou contournable |
| ❌ | non appliqué, ou contraire à la règle |
| ∅ | fonctionnalité absente de cette couche |
| 🕳 | appliqué **seulement** dans le `localStorage`, donc sans effet réel |

La colonne **Protégée ?** répond à une seule question : un utilisateur peut-il
enfreindre la règle en appelant directement l'API ?

---

## 1. Factures — le cœur du besoin comptable

| ID | Règle attendue | Source | UI | API | Base | Protégée ? | Constat |
|---|---|---|---|---|---|---|---|
| R-FAC-01 | **Seul l'admin génère des factures** | description du produit | ⚠️ 🕳 bouton réservé à l'admin (`InvoicesView.tsx:138`, `:414`), mais la facture va dans le `localStorage` | ❌ le router autorise `rh`, `admin` **et `accountant`** (`invoicing.py:14`). La règle « admin seulement » (`main.py:395`) est du code mort, masqué. | ❌ rien ne lie `cree_par_id` à un rôle ; la colonne est nullable | **Non** : la comptable peut créer une facture par l'API | La règle est inversée côté serveur. La séparation des responsabilités (celle qui crée ≠ celle qui approuve) n'est pas garantie. |
| R-FAC-02 | **La comptable approuve ou refuse les factures** | description du produit | ∅ | ∅ | ∅ ni statut ni colonne | — | **Fonctionnalité centrale absente des trois couches.** |
| R-FAC-03 | **La comptable est notifiée des factures en attente** | description du produit | ∅ (les notifications sont par rôle, dans le `localStorage`) | ∅ | ∅ | — | absente |
| R-FAC-04 | **Filtrer par jour, par mois, par client** | description du produit | ❌ statut et recherche texte seulement (`InvoicesView.tsx:99-103`) | ❌ `GET /api/invoices` n'accepte aucun paramètre | ⚠️ les colonnes existent (`date_emission`, `client_id`), mais sans index (Q-PERF-006, Q-PERF-007) | — | absente |
| R-FAC-05 | Seuls l'admin et la comptable voient les factures | Sidebar (`Sidebar.tsx:51-52`) | ⚠️ 🕳 ce sont des données fictives locales | ❌ **`/api/data` renvoie toutes les factures à tout rôle connecté**, employé compris (`main.py:500`). Le router, lui, filtre correctement. | ∅ pas de RLS | **Non** | La protection du router est contournée par `/api/data`. |
| R-FAC-06 | Modifier une facture : qui, et dans quel état ? | `UNKNOWN / NEEDS VERIFICATION` | ∅ | ∅ aucun endpoint | ∅ | — | Aucune modification possible. Il faut décider si une facture émise est modifiable : la pratique comptable l'interdit généralement, en passant par un avoir. |
| R-FAC-07 | Supprimer une facture : interdit ou annulation | `UNKNOWN / NEEDS VERIFICATION` (le statut `annulee` existe en base) | ∅ | ∅ | ⚠️ suppression SQL bloquée par `invoice_items` (`NO ACTION`), mais autorisée en cascade par l'ORM | — | Aucune règle définie. L'ENUM `annulee` suggère une annulation logique, qu'aucun code n'utilise. |
| R-FAC-08 | Transitions de statut contrôlées (brouillon → envoyée → payée) | sous-entendu par l'ENUM | ❌ le statut est **choisi librement** à la création, dans une liste (`InvoicesView.tsx:450-453`) | ❌ aucune transition ; statut jamais positionné (NULL) | ❌ ENUM sans contrôle des transitions ; nullable | — | Il n'existe aucune machine à états. `Overdue` est saisi à la main, alors qu'il devrait se calculer à partir de l'échéance. |
| R-FAC-09 | Numérotation unique, continue, croissante | obligation légale de facturation ; ticket #38 | 🕳 `INV-2024-00{n+1}` local | ⚠️ `FA-AAAA-{count+1}` | ⚠️ `UNIQUE(numero)` seulement | partiellement : l'unicité est garantie, pas la continuité | voir T2, `08-data-integrity/transactions-and-concurrency.md` |
| R-FAC-10 | Les montants découlent des lignes et de la TVA | pratique comptable | ❌ montant saisi à la main, sans TVA | ✅ calculés côté serveur, montant client ignoré | ❌ aucune cohérence imposée entre en-tête et lignes (Q-INT-012) | API seulement | |
| R-FAC-11 | Seuls l'admin et la comptable téléchargent le PDF | Sidebar | ⚠️ | ✅ `rh`, `admin`, `accountant` | — | **Oui** | contrôle correct |

## 2. Comptes et accès

| ID | Règle attendue | Source | UI | API | Base | Protégée ? | Constat |
|---|---|---|---|---|---|---|---|
| R-USR-01 | Seul l'admin crée des comptes | ticket #9 | ✅ (`UsersView.tsx:118`) | ✅ (`main.py:226`) | — | **Oui** | contrôle correct, mais la création est probablement cassée (OBS-021) |
| R-USR-02 | **Seul l'admin modifie un compte, dont le rôle** | sous-entendu | 🕳 **modification locale seulement** (`App.tsx:485-487`) | ∅ aucun endpoint | ❌ rôle en chaîne libre | — | 🔴 **L'admin croit avoir changé un rôle ; le serveur n'a pas changé.** |
| R-USR-03 | **Un compte supprimé ou désactivé ne peut plus se connecter** | sous-entendu (`isActive` existe) | 🕳 **suppression locale seulement** (`App.tsx:489-493`) | ❌ ni endpoint de suppression ou de désactivation, ni contrôle de `isActive` (OBS-011) | ⚠️ la colonne `isActive` existe | **Non** | 🔴 **Un employé « supprimé » dans l'UI conserve un accès complet à l'API.** C'est le défaut de révocation d'accès le plus grave du système : départ d'un salarié, compte compromis… |
| R-USR-04 | Un rôle par utilisateur, parmi admin, employee ou accountant | `types.ts:1` | ✅ liste fermée | ❌ chaîne libre acceptée (`main.py:174`) | ❌ aucune contrainte | **Non** : un admin peut créer un rôle `rh` ou une faute de frappe | Un compte créé avec `"Admin"` (majuscule) n'aurait aucun droit, sans qu'aucune erreur ne le signale. |
| R-USR-05 | Un employé = un seul compte | `UNKNOWN / NEEDS VERIFICATION` | — | ⚠️ unicité exacte de l'e-mail seulement | ⚠️ `UNIQUE(email)` sensible à la casse | partiellement | `Alice@…` et `alice@…` donnent deux comptes (Q-INT-004) |
| R-USR-06 | La comptable consulte les comptes en lecture seule | Sidebar, `UsersView.tsx:115` | ✅ | ⚠️ aucune écriture possible, mais lecture de **tous** les comptes via `/api/data`, ouverte à **tous** les rôles | — | lecture non restreinte | Un employé lit aussi la liste complète des comptes, avec e-mail, rôle et département. |
| R-USR-07 | L'utilisateur choisit son mot de passe ; mot de passe robuste | sous-entendu | — | ❌ aucune politique de complexité (`main.py:183-185`) | — | **Non** | |
| R-USR-08 | Changer de rôle dans l'UI exige d'avoir ce rôle | sous-entendu | ❌ **« Switch to Admin View » proposé à tous** (`Sidebar.tsx:154-159`) | ✅ le serveur relit le rôle en base | — | ✅ côté serveur | défaut d'interface, sans fuite serveur |

## 3. Congés

| ID | Règle attendue | Source | UI | API | Base | Protégée ? | Constat |
|---|---|---|---|---|---|---|---|
| R-CNG-01 | Un employé crée une demande **pour lui-même** | sous-entendu | 🕳 | ❌ **anonyme**, `employeeId` libre, donc usurpation possible ; plante en pratique (OBS-008) | ❌ `employee_id` nullable | **Non** | |
| R-CNG-02 | **Seul l'admin approuve ou refuse** | `App.tsx:299`, `:316` ; router mort `require_roles("rh","admin")` | 🕳 admin seulement (`TeamView.tsx:174`) | ❌ **anonyme** (`main.py:354-371`) | ❌ le valideur n'est jamais enregistré | **Non** | |
| R-CNG-03 | Un employé ne valide pas sa propre demande | sous-entendu | — | ∅ | ❌ aucune contrainte `valide_par_id <> employee_id` | **Non** | |
| R-CNG-04 | Une décision prise est définitive (ou la règle de révision est définie) | `UNKNOWN / NEEDS VERIFICATION` | ❌ | ❌ aucune transition | ❌ | **Non** | |
| R-CNG-05 | La comptable n'a pas accès aux congés | ticket #47, `Sidebar.tsx:53-55` | ✅ menu masqué | ❌ `/api/data` lui renvoie **toutes** les demandes, y compris les motifs et les arrêts maladie | — | **Non** | La correction de #47 ne porte que sur l'interface. |
| R-CNG-06 | Pas de chevauchement de congés pour un même employé | `UNKNOWN / NEEDS VERIFICATION` | ❌ | ❌ | ❌ aucune contrainte d'exclusion | **Non** | |
| R-CNG-07 | Le solde de congés est décompté | `EmployeeOut.solde_conges` (`schemas/user.py:37`) | ∅ | ∅ | ∅ **aucune colonne** | — | prévu dans le code mort, jamais modélisé |

## 4. Bulletins de paie

| ID | Règle attendue | Source | UI | API | Base | Protégée ? | Constat |
|---|---|---|---|---|---|---|---|
| R-PAY-01 | **Un employé ne voit que ses propres bulletins** | ticket #10 | ❌ 🕳 le type frontend n'a pas de lien employé : **tout employé voit la même liste** | ✅ filtre `employee_id = current_user.id` (`main.py:509`) | ✅ FK obligatoire | **Oui** côté serveur | C'est le seul contrôle de propriété du système, et l'UI ne s'en sert pas. |
| R-PAY-02 | La comptable voit tous les bulletins | ticket #12 (« Do not revert », `Sidebar.tsx:58-59`) | ✅ | ✅ (`main.py:505`) | — | **Oui** | conforme |
| R-PAY-03 | L'admin voit les bulletins | `UNKNOWN / NEEDS VERIFICATION` | ❌ **l'onglet « payslips » affiche la vue Factures** pour un admin (`App.tsx`, `case 'payslips'`) | ✅ l'admin reçoit tout | — | — | Règle non définie : l'UI et l'API divergent. |
| R-PAY-04 | Qui émet un bulletin ? | `UNKNOWN / NEEDS VERIFICATION` (router mort : `rh`, `admin`) | ∅ | ∅ aucun endpoint monté | ✅ `UNIQUE(employee_id, periode)` | — | Il n'existe **aucun moyen** de créer un bulletin. |
| R-PAY-05 | Net ≤ brut | pratique de paie | — | ∅ | ❌ aucun CHECK | **Non** | |

## 5. Équipe, appareils, projets, documents

| ID | Règle attendue | UI | API | Base | Protégée ? | Constat |
|---|---|---|---|---|---|---|
| R-EQP-01 | Seul l'admin ajoute un membre d'équipe | 🕳 | ❌ **anonyme** (`main.py:373`) | ❌ aucun lien vers `users` | **Non** | voir OBS-007 |
| R-DEV-01 | Seul l'admin gère les appareils | ∅ aucune UI | ⚠️ intention correcte (`main.py:435`), mais les routes plantent (OBS-010) | ❌ numéro de série non unique | indéterminé | |
| R-DEV-02 | Un appareil n'est vendu qu'une fois, et se rattache à sa facture | ∅ | ❌ code mort | ∅ aucun lien | **Non** | ticket #18 fermé sans lien en base |
| R-PRJ-01 | Seul l'admin gère les projets | 🕳 | ∅ | ∅ | — | entité locale uniquement |
| R-DOC-01 | **Un employé demande un document administratif** | ∅ | ∅ | ∅ | — | **fonctionnalité citée par la description du produit, absente des trois couches** |

---

## 6. Synthèse

| | Règles |
|---|---|
| Règles évaluées | 36 |
| **Protégées côté serveur** | **6** : R-FAC-10, R-FAC-11, R-USR-01, R-USR-08, R-PAY-01, R-PAY-02 |
| Protégées partiellement | 2 : R-FAC-09 (unicité sans continuité), R-USR-05 (unicité sensible à la casse) |
| **Enfreignables par un appel direct à l'API** | **15** : R-FAC-01, R-FAC-05, R-USR-03, R-USR-04, R-USR-06, R-USR-07, R-CNG-01 à R-CNG-06, R-PAY-05, R-EQP-01, R-DEV-02 |
| Fonctionnalités inexistantes, sans aucun moyen de les exercer | 5 : R-FAC-02, R-FAC-03, R-CNG-07, R-PAY-04, R-DOC-01 |
| Règles dont l'UI simule l'effet sans que le serveur l'applique (🕳) | 10 : R-FAC-01, R-FAC-05, R-FAC-09, R-USR-02, R-USR-03, R-CNG-01, R-CNG-02, R-PAY-01, R-EQP-01, R-PRJ-01 |
| Règles à faire préciser par le métier | 7 (`UNKNOWN / NEEDS VERIFICATION`) |
| Non évaluable à ce stade | R-DEV-01 : les routes plantent avant le contrôle (OBS-010, à prouver) |

### Les trois constats les plus lourds de conséquences

1. **La révocation d'accès est illusoire (R-USR-02, R-USR-03).** Supprimer un
   compte, le désactiver ou changer son rôle n'a aucun effet côté serveur, alors
   que l'interface affiche une réussite.
2. **Le circuit comptable n'existe pas (R-FAC-02 à R-FAC-04),** et la
   séparation des responsabilités entre création et approbation est inversée
   côté serveur (R-FAC-01).
3. **Les restrictions de lecture par rôle sont contournées par `/api/data`
   (R-FAC-05, R-USR-06, R-CNG-05).** Les tickets #10, #12 et #47 ont été
   corrigés **dans l'interface seulement**.

### Règles à faire valider par le métier avant la remédiation

R-FAC-06, R-FAC-07, R-USR-05, R-CNG-04, R-CNG-06, R-PAY-03 et R-PAY-04.
