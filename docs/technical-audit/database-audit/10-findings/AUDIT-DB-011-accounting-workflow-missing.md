# AUDIT-DB-011 — Le circuit comptable n'existe pas : ni approbation, ni notification, ni filtres

## Sévérité
HIGH

**Justification :**
- **Impact :** c'est le besoin **central** énoncé pour le profil comptable :
  être notifiée des factures en attente, les approuver ou les refuser, les
  filtrer par jour, mois et client. Il n'est supporté **ni par le modèle de
  données, ni par l'API, ni par l'interface**.
- **Critère HIGH rempli :** une fonctionnalité métier centrale est inopérante.
- **Ce n'est pas une faille,** donc pas CRITICAL.

## Catégorie
Règles métier / Modèle de données

## Statut
OPEN · CONFIRMED

## Résumé
Le schéma ne contient :
- aucun statut d'approbation, aucun valideur, aucune date ni motif de décision ;
- aucune table de notifications ;
- aucun index pour les filtres attendus.

Aucun endpoint ne permet de décider d'une facture ni de filtrer la liste, et
aucune action d'approbation n'existe dans `InvoicesView`.

## Détails techniques

| Besoin | Modèle de données | API | Interface |
|---|---|---|---|
| Approuver ou refuser une facture | ∅ : l'ENUM `invoicestatus` (`BROUILLON, ENVOYEE, PAYEE, EN_RETARD, ANNULEE`) n'a pas d'état d'approbation | ∅ | ∅ |
| Tracer qui a décidé, quand et pourquoi | ∅ | ∅ | ∅ |
| Notifier les factures en attente | ∅ aucune table | ∅ | notifications par rôle dans le `localStorage` |
| Filtrer par jour, mois ou client | les colonnes existent, mais **aucun index utilisable** (Q-PERF-013 à 015) | ∅ aucun paramètre sur `GET /api/invoices` | filtre par statut et recherche texte seulement (`InvoicesView.tsx:99-103`) |
| Transitions de statut contrôlées | ∅ aucune règle | ∅ aucun endpoint | statut choisi librement à la création (`InvoicesView.tsx:450-453`) |
| Facture entrante ou sortante | ∅ (ticket #40) | ∅ | ∅ |

Le statut `Overdue` (`en_retard`) est **saisi** dans l'interface, alors qu'il
est **dérivable** de `date_echeance` et de l'état de paiement.

## Impact métier
La comptable ne peut pas faire son travail dans la plateforme. Toute
approbation passe hors du système, sans aucune trace.

## Preuves
- Q-DISC-005 et Q-SCH-001 : inventaire complet des tables et des colonnes, sans
  aucun élément d'approbation.
- Q-SCH-009 : valeurs de l'ENUM.
- Q-PERF-013 à 015 : aucun index utilisable pour les filtres.
- `09-business-rules/business-rules-matrix.md` : R-FAC-02, R-FAC-03, R-FAC-04
  et R-FAC-08.

## Composants concernés
`app/models/invoicing.py`, `app/routers/invoicing.py`,
`src/components/InvoicesView.tsx`.

## Localisation
- **Code :** `app/models/invoicing.py:14-49`, `app/routers/invoicing.py:50-52`.
- **Base :** `invoices`, ENUM `invoicestatus`.

## Cause racine
Le modèle de facture a été conçu pour l'**émission**, et non pour le
**contrôle**. Le besoin comptable n'a pas été modélisé.

## Recommandation
Modéliser explicitement le circuit, à valider avec le métier avant tout
développement :
- un **cycle de vie** séparant l'émission de l'approbation, par exemple :
  `BROUILLON → SOUMISE → APPROUVEE / REJETEE → ENVOYEE → PAYEE`, plus
  `ANNULEE` ;
- une **table de décisions** `invoice_reviews`, avec `invoice_id`,
  `reviewer_id`, `decision`, `comment` et `decided_at`. Elle conserve
  l'historique, y compris une nouvelle soumission après un refus ;
- une **table `notifications`**, avec `user_id`, `type`, `ref` et `read_at`,
  alimentée lors de la soumission ;
- des **index** : `(statut, date_emission)` et `(client_id, date_emission)` ;
- des **endpoints** :
  - `GET /api/invoices?status=&from=&to=&client_id=&page=` ;
  - `POST /api/invoices/{id}/submit` ;
  - `POST /api/invoices/{id}/approve` et `/reject`, réservés à la comptable.

## Correctif proposé
Ce point ne peut pas être corrigé seul : c'est un **chantier de conception**.
La première étape est un atelier avec le métier, pour figer les états, les
transitions et les rôles.

## Risques du correctif
La règle de séparation des responsabilités doit être imposée : la comptable ne
peut pas approuver une facture qu'elle aurait créée. Cela dépend
d'AUDIT-DB-010.

## Validation
- Scénario de bout en bout : l'admin crée et soumet, la comptable est notifiée,
  filtre par mois, puis approuve. La décision est tracée.
- Un refus suivi d'une nouvelle soumission conserve l'historique.

## Effort estimé
XL.

## Dépendances
AUDIT-DB-010, AUDIT-DB-012, AUDIT-DB-014, AUDIT-DB-015, AUDIT-DB-017,
AUDIT-DB-018 ; tickets #40 et #41.

## Findings liés
AUDIT-DB-001, AUDIT-DB-010, AUDIT-DB-017.
