# Résultats — 03-data-integrity.sql

- **Généré le :** 2026-10-02T11:32:22
- **Cible :** `postgresql://localhost:5432/dixpertia` (identifiants masqués)
- **Mode :** lecture seule (`default_transaction_read_only = on`, chaque requête annulée par rollback)
- **Source :** `docs/technical-audit/database-audit/01-requests/sql/03-data-integrity.sql`

- **Lecture seule confirmée par le serveur :** `on`

## Q-INT-001

**Objectif :** Volume de chaque table, pour interpréter les résultats suivants (une absence d'anomalie sur une table vide n'est pas une preuve).

**Résultat attendu :** users = 4 ; autres tables = 0 avant tout jeu de démonstration.

```sql
SELECT 'users' AS t, count(*) FROM users UNION ALL
SELECT 'team_members', count(*) FROM team_members UNION ALL
SELECT 'payslips', count(*) FROM payslips UNION ALL
SELECT 'leave_requests', count(*) FROM leave_requests UNION ALL
SELECT 'clients', count(*) FROM clients UNION ALL
SELECT 'invoices', count(*) FROM invoices UNION ALL
SELECT 'invoice_items', count(*) FROM invoice_items UNION ALL
SELECT 'devices', count(*) FROM devices UNION ALL
SELECT 'services', count(*) FROM services;
```

**Résultat observé :** 9 ligne(s)

| t | count |
|---|---|
| users | 4 |
| team_members | 0 |
| payslips | 0 |
| leave_requests | 0 |
| clients | 0 |
| invoices | 0 |
| invoice_items | 0 |
| devices | 0 |
| services | 0 |

## Q-INT-002

**Objectif :** Utilisateurs par rôle, et rôles hors de la liste attendue (admin, employee, accountant).

**Résultat attendu :** uniquement les trois rôles attendus ; aucun rôle NULL.

```sql
SELECT COALESCE(role, '<NULL>') AS role, count(*) AS users,
       (role IS NULL OR role NOT IN ('admin','employee','accountant')) AS unexpected
FROM users GROUP BY role ORDER BY 1;
```

**Résultat observé :** 2 ligne(s)

| role | users | unexpected |
|---|---|---|
| accountant | 1 | False |
| admin | 3 | False |

## Q-INT-003

**Objectif :** Utilisateurs avec des attributs obligatoires manquants (rôle, hash, prénom, nom, date de création).

**Résultat attendu :** 0 partout.

```sql
SELECT count(*) FILTER (WHERE role IS NULL) AS no_role,
       count(*) FILTER (WHERE "hashedPassword" IS NULL OR "hashedPassword" = '') AS no_password_hash,
       count(*) FILTER (WHERE "firstName" IS NULL OR "firstName" = '') AS no_first_name,
       count(*) FILTER (WHERE "lastName" IS NULL OR "lastName" = '') AS no_last_name,
       count(*) FILTER (WHERE "createdAt" IS NULL) AS no_created_at,
       count(*) FILTER (WHERE "isActive" IS NULL) AS null_is_active
FROM users;
```

**Résultat observé :** 1 ligne(s)

| no_role | no_password_hash | no_first_name | no_last_name | no_created_at | null_is_active |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 |

## Q-INT-004

**Objectif :** Doublons d'e-mail insensibles à la casse (la contrainte UNIQUE est sensible à la casse).

**Résultat attendu :** 0. Une valeur > 0 prouve qu'une même personne peut avoir deux comptes (Alice@x.tn / alice@x.tn).

```sql
SELECT count(*) AS duplicate_groups, COALESCE(sum(n), 0) AS accounts_involved
FROM (SELECT count(*) AS n FROM users GROUP BY lower(email) HAVING count(*) > 1) d;
```

**Résultat observé :** 1 ligne(s)

| duplicate_groups | accounts_involved |
|---|---|
| 0 | 0 |

## Q-INT-005

**Objectif :** Format des identifiants utilisateur, et trous dans la séquence USR-NNN (cause de la collision count()+1).

**Résultat attendu :** identifiants au format USR-NNN ; tout trou rend `USR-{count()+1}` (main.py:235) susceptible de collision.

```sql
SELECT id, (id ~ '^USR-[0-9]{3,}$') AS well_formed,
       row_number() OVER (ORDER BY id) AS position,
       NULLIF(regexp_replace(id, '\D', '', 'g'), '')::int AS numeric_part
FROM users ORDER BY id;
```

**Résultat observé :** 4 ligne(s)

| id | well_formed | position | numeric_part |
|---|---|---|---|
| USR-001 | True | 1 | 1 |
| USR-003 | True | 2 | 3 |
| USR-005 | True | 3 | 5 |
| USR-006 | True | 4 | 6 |

## Q-INT-006

**Objectif :** Prochain identifiant que POST /api/users va générer (main.py:235) et s'il existe déjà.

**Résultat attendu :** l'identifiant généré doit être libre. Si already_taken = true, la création de compte échoue (violation de PK).

```sql
SELECT format('USR-%s', lpad((count(*)+1)::text, 3, '0')) AS id_generated_by_api,
       EXISTS (SELECT 1 FROM users u2 WHERE u2.id = format('USR-%s', lpad(((SELECT count(*) FROM users)+1)::text, 3, '0'))) AS already_taken
FROM users;
```

**Résultat observé :** 1 ligne(s)

| id_generated_by_api | already_taken |
|---|---|
| USR-005 | True |

## Q-INT-007

**Objectif :** Jetons de réinitialisation présents en base, et jetons expirés non nettoyés.

**Résultat attendu :** 0 jeton expiré conservé. Valeurs jamais affichées — comptage uniquement.

```sql
SELECT count(*) FILTER (WHERE "resetToken" IS NOT NULL) AS tokens_stored,
       count(*) FILTER (WHERE "resetToken" IS NOT NULL AND ("resetTokenExpiry" IS NULL OR "resetTokenExpiry" < now() AT TIME ZONE 'UTC')) AS tokens_expired_or_without_expiry
FROM users;
```

**Résultat observé :** 1 ligne(s)

| tokens_stored | tokens_expired_or_without_expiry |
|---|---|
| 0 | 0 |

## Q-INT-008

**Objectif :** Comptes inactifs ou non vérifiés (pour le test OBS-011 : un compte inactif peut-il se connecter ?).

**Résultat attendu :** inventaire seulement.

```sql
SELECT "isActive" AS is_active, "isVerified" AS is_verified, count(*) FROM users GROUP BY 1, 2 ORDER BY 1, 2;
```

**Résultat observé :** 2 ligne(s)

| is_active | is_verified | count |
|---|---|---|
| True | False | 2 |
| True | True | 2 |

## Q-INT-009

**Objectif :** Orphelins logiques entre team_members et users (aucune FK ne les relie).

**Résultat attendu :** chaque membre d'équipe correspond à un compte, et inversement — à confirmer comme règle métier en phase 9.

```sql
SELECT
  (SELECT count(*) FROM team_members tm WHERE NOT EXISTS (SELECT 1 FROM users u WHERE lower(u.email)=lower(tm.email))) AS members_without_account,
  (SELECT count(*) FROM users u WHERE u.role='employee' AND NOT EXISTS (SELECT 1 FROM team_members tm WHERE lower(tm.email)=lower(u.email))) AS employees_without_member_profile;
```

**Résultat observé :** 1 ligne(s)

| members_without_account | employees_without_member_profile |
|---|---|
| 0 | 0 |

## Q-INT-010

**Objectif :** Orphelins sur les clés étrangères déclarées (ne doit jamais arriver si la FK existe réellement en base).

**Résultat attendu :** 0 partout. Une valeur > 0 prouverait que la FK est absente du schéma réel.

```sql
SELECT
  (SELECT count(*) FROM payslips p WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id=p.employee_id)) AS payslips_orphan_employee,
  (SELECT count(*) FROM leave_requests l WHERE l.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id=l.employee_id)) AS leaves_orphan_employee,
  (SELECT count(*) FROM leave_requests l WHERE l.valide_par_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id=l.valide_par_id)) AS leaves_orphan_validator,
  (SELECT count(*) FROM invoices i WHERE NOT EXISTS (SELECT 1 FROM clients c WHERE c.id=i.client_id)) AS invoices_orphan_client,
  (SELECT count(*) FROM invoices i WHERE i.cree_par_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id=i.cree_par_id)) AS invoices_orphan_creator,
  (SELECT count(*) FROM invoice_items it WHERE NOT EXISTS (SELECT 1 FROM invoices i WHERE i.id=it.invoice_id)) AS items_orphan_invoice;
```

**Résultat observé :** 1 ligne(s)

| payslips_orphan_employee | leaves_orphan_employee | leaves_orphan_validator | invoices_orphan_client | invoices_orphan_creator | items_orphan_invoice |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 |

## Q-INT-011

**Objectif :** Factures dans un état incohérent : sans statut, sans montant, sans créateur, sans ligne, échéance avant émission.

**Résultat attendu :** 0 partout.

```sql
SELECT count(*) FILTER (WHERE statut IS NULL) AS no_status,
       count(*) FILTER (WHERE montant_ht IS NULL OR montant_ttc IS NULL) AS no_amount,
       count(*) FILTER (WHERE cree_par_id IS NULL) AS no_creator,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM invoice_items it WHERE it.invoice_id=i.id)) AS no_items,
       count(*) FILTER (WHERE date_echeance < date_emission) AS due_before_issue,
       count(*) FILTER (WHERE montant_ht < 0 OR montant_ttc < 0) AS negative_amount,
       count(*) FILTER (WHERE montant_ttc < montant_ht) AS ttc_below_ht
FROM invoices i;
```

**Résultat observé :** 1 ligne(s)

| no_status | no_amount | no_creator | no_items | due_before_issue | negative_amount | ttc_below_ht |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Q-INT-012

**Objectif :** Montants stockés incohérents avec la somme des lignes (montant_ht/ttc sont des valeurs dérivées).

**Résultat attendu :** 0 facture dont le montant diffère de la somme recalculée.

```sql
SELECT i.id, i.numero,
       i.montant_ht AS stored_ht, round(sum(it.quantite*it.prix_unitaire), 2) AS computed_ht,
       i.montant_ttc AS stored_ttc, round(sum(it.quantite*it.prix_unitaire*(1+it.taux_tva/100)), 2) AS computed_ttc
FROM invoices i JOIN invoice_items it ON it.invoice_id=i.id
GROUP BY i.id
HAVING i.montant_ht IS DISTINCT FROM round(sum(it.quantite*it.prix_unitaire), 2)
    OR i.montant_ttc IS DISTINCT FROM round(sum(it.quantite*it.prix_unitaire*(1+it.taux_tva/100)), 2);
```

**Résultat observé :** 0 ligne(s)


## Q-INT-013

**Objectif :** Lignes de facture invalides : quantité nulle ou négative, prix négatif, taux de TVA hors plage.

**Résultat attendu :** 0 partout.

```sql
SELECT count(*) FILTER (WHERE quantite IS NULL OR quantite <= 0) AS bad_quantity,
       count(*) FILTER (WHERE prix_unitaire < 0) AS negative_price,
       count(*) FILTER (WHERE taux_tva IS NULL OR taux_tva < 0 OR taux_tva > 100) AS bad_vat_rate
FROM invoice_items;
```

**Résultat observé :** 1 ligne(s)

| bad_quantity | negative_price | bad_vat_rate |
|---|---|---|
| 0 | 0 | 0 |

## Q-INT-014

**Objectif :** Numéros de facture : formats coexistants et trous dans la numérotation par année (ticket #38).

**Résultat attendu :** un seul format ; numérotation continue.

```sql
SELECT CASE WHEN numero ~ '^FA-[0-9]{4}-[0-9]{4}$' THEN 'FA-YYYY-NNNN'
            WHEN numero ~ '^INV-[0-9]{4}-[0-9]+$' THEN 'INV-YYYY-NNN'
            ELSE 'other' END AS format, count(*)
FROM invoices GROUP BY 1;
```

**Résultat observé :** 0 ligne(s)


## Q-INT-015

**Objectif :** Congés incohérents : sans employé, date de fin avant date de début, décision sans valideur.

**Résultat attendu :** 0 partout.

```sql
SELECT count(*) FILTER (WHERE employee_id IS NULL) AS no_employee,
       count(*) FILTER (WHERE date_fin < date_debut) AS end_before_start,
       count(*) FILTER (WHERE statut IN ('APPROUVE','REFUSE') AND valide_par_id IS NULL) AS decided_without_validator,
       count(*) FILTER (WHERE valide_par_id IS NOT NULL AND valide_par_id = employee_id) AS self_validated
FROM leave_requests;
```

**Résultat observé :** 1 ligne(s)

| no_employee | end_before_start | decided_without_validator | self_validated |
|---|---|---|---|
| 0 | 0 | 0 | 0 |

## Q-INT-016

**Objectif :** Congés qui se chevauchent pour un même employé.

**Résultat attendu :** 0 (aucune contrainte d'exclusion n'empêche le chevauchement).

```sql
SELECT a.employee_id, a.id AS leave_a, b.id AS leave_b
FROM leave_requests a JOIN leave_requests b
  ON a.employee_id=b.employee_id AND a.id < b.id
 AND daterange(a.date_debut, a.date_fin, '[]') && daterange(b.date_debut, b.date_fin, '[]');
```

**Résultat observé :** 0 ligne(s)


## Q-INT-017

**Objectif :** Bulletins de paie invalides : net supérieur au brut, montants négatifs.

**Résultat attendu :** 0 partout.

```sql
SELECT count(*) FILTER (WHERE montant_net > montant_brut) AS net_above_gross,
       count(*) FILTER (WHERE montant_brut < 0 OR montant_net < 0) AS negative
FROM payslips;
```

**Résultat observé :** 1 ligne(s)

| net_above_gross | negative |
|---|---|
| 0 | 0 |

## Q-INT-018

**Objectif :** Appareils : statuts hors liste, numéros de série dupliqués ou manquants, prix invalides.

**Résultat attendu :** statuts dans {Available, Sold, ...} ; numéros de série uniques.

```sql
SELECT COALESCE(status,'<NULL>') AS status, count(*),
       count(*) FILTER (WHERE "serialNumber" IS NULL OR "serialNumber"='') AS no_serial,
       count(*) FILTER (WHERE price IS NULL OR price < 0) AS bad_price
FROM devices GROUP BY status;
```

**Résultat observé :** 0 ligne(s)


## Q-INT-019

**Objectif :** Numéros de série d'appareils dupliqués (aucune contrainte UNIQUE déclarée).

**Résultat attendu :** 0.

```sql
SELECT "serialNumber", count(*) FROM devices WHERE "serialNumber" IS NOT NULL GROUP BY 1 HAVING count(*) > 1;
```

**Résultat observé :** 0 ligne(s)


## Q-INT-020

**Objectif :** Clients en doublon (même nom, insensible à la casse) — aucune contrainte UNIQUE déclarée.

**Résultat attendu :** 0.

```sql
SELECT lower(nom) AS normalised_name, count(*) FROM clients GROUP BY 1 HAVING count(*) > 1;
```

**Résultat observé :** 0 ligne(s)


