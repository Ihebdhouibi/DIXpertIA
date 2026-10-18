# Résultats — sondage des contraintes d'intégrité

- **Exécuté le :** 2026-10-02T11:37:30
- **Script :** `01-requests/scripts/run_constraint_probe.py`
- **Méthode :** chaque tentative dans un SAVEPOINT, le tout dans une transaction **toujours annulée**
- **Lignes résiduelles après rollback :** `0` (attendu : 0)

**Lecture :** une règle « ACCEPTÉE » n'est **pas** garantie par la base ; seule l'application
pourrait l'appliquer, et la Phase 9 montre qu'elle ne le fait pas non plus.

| Sonde | Règle métier | Source | Base | Détail |
|---|---|---|---|---|
| P-01 | Une facture a un montant positif | pratique comptable | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-02 | L'échéance n'est pas antérieure à l'émission | pratique comptable | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-03 | Le TTC n'est pas inférieur au HT | pratique comptable | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-04 | Une facture a toujours un statut | R-FAC-08 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-05 | Une facture a toujours un montant | pratique comptable | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-06 | Une facture a toujours un auteur | R-FAC-01, traçabilité | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-07 | Les montants de l'en-tête correspondent aux lignes | valeur dérivée | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-08 | Une ligne a une quantité strictement positive | pratique comptable | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-09 | Le taux de TVA est compris entre 0 et 100 | fiscal | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-10 | Le taux de TVA n'est pas négatif | fiscal | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-11 | Une ligne a un prix positif | pratique comptable | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-12 | Une demande de congé a un employé | R-CNG-01 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-13 | Un congé finit après avoir commencé | bon sens | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-14 | Un employé ne valide pas sa propre demande | R-CNG-03 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-15 | Une décision de congé est attribuée à un valideur | R-CNG-02, traçabilité | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-16 | Deux congés d'un même employé ne se chevauchent pas | R-CNG-06 (à confirmer) | **ACCEPTÉE** | 2 ligne(s) affectée(s) |
| P-17 | Le salaire net ne dépasse pas le brut | R-PAY-05 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-18 | Les montants de paie sont positifs | R-PAY-05 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-19 | Un seul bulletin par employé et par mois (contrôle attendu : rejet) | uq_employee_periode | **REJETÉE** | ERREUR:  la valeur d'une clé dupliquée rompt la contrainte unique « uq_employee_periode » |
| P-20 | Deux bulletins dans le même mois avec des jours différents | uq_employee_periode porte sur une DATE, pas sur un mois | **ACCEPTÉE** | 2 ligne(s) affectée(s) |
| P-21 | Un rôle appartient à la liste admin / employee / accountant | R-USR-04 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-22 | Un compte a un mot de passe et un rôle | R-USR-04 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-23 | Un e-mail = un seul compte, quelle que soit la casse | R-USR-05 | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-24 | Un compte inséré sans valeur explicite est actif ou inactif, jamais indéterminé | valeurs par défaut côté Python seulement | **ACCEPTÉE** | 1 ligne(s) affectée(s) — {'is_active_null': True} |
| P-25 | Deux appareils n'ont pas le même numéro de série | inventaire | **ACCEPTÉE** | 2 ligne(s) affectée(s) |
| P-26 | Un appareil a un prix positif et un statut connu | inventaire | **ACCEPTÉE** | 1 ligne(s) affectée(s) |
| P-27 | Deux clients ne portent pas le même nom | R-FAC-04 (filtre par client) | **ACCEPTÉE** | 2 ligne(s) affectée(s) |
| P-28 | Supprimer une facture en SQL direct (FK invoice_items sans ON DELETE) | contrôle attendu : rejet | **REJETÉE** | ERREUR:  UPDATE ou DELETE sur la table « invoices » viole la contrainte de clé étrangère « invoice_items_invoice_id_fkey » de la table « invoice_items » |
| P-29 | Supprimer un utilisateur qui a des congés (FK NO ACTION) | contrôle attendu : rejet | **REJETÉE** | ERREUR:  UPDATE ou DELETE sur la table « users » viole la contrainte de clé étrangère « payslips_employee_id_fkey » de la table « payslips » |
| P-30 | Une facture référence un client existant (FK) | contrôle attendu : rejet | **REJETÉE** | ERREUR:  une instruction insert ou update sur la table « invoices » viole la contrainte de clé |

**26 sondes acceptées sur 30.**

## Liaison des ENUM par SQLAlchemy (`invoices.statut`)

La base stocke les **noms** des membres (Q-SCH-009 : `BROUILLON, ENVOYEE, …`).

| Valeur passée par le code | Résultat |
|---|---|
| `BROUILLON` | accepté, envoyé à la base comme 'BROUILLON' |
| `brouillon` | accepté, envoyé à la base comme 'BROUILLON' |

`insert_invoices.py:110-119` passe la **valeur** (`"brouillon"`, `"payee"`…).
