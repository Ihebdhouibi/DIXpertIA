-- Phase 5 — Intégrité des données.
-- Lecture seule. Les requêtes ne renvoient que des comptages et des identifiants techniques
-- (USR-NNN, id entiers) : jamais d'e-mail, de nom, de hash, de jeton ni de montant individuel.
-- Note : au 2026-10-01, seule la table users contient des lignes. Un résultat vide sur une
-- table vide ne prouve rien ; il est rapporté comme tel dans 08-data-integrity/.

-- @id: Q-INT-001
-- @purpose: Volume de chaque table, pour interpréter les résultats suivants (une absence d'anomalie sur une table vide n'est pas une preuve).
-- @expected: users = 4 ; autres tables = 0 avant tout jeu de démonstration.
SELECT 'users' AS t, count(*) FROM users UNION ALL
SELECT 'team_members', count(*) FROM team_members UNION ALL
SELECT 'payslips', count(*) FROM payslips UNION ALL
SELECT 'leave_requests', count(*) FROM leave_requests UNION ALL
SELECT 'clients', count(*) FROM clients UNION ALL
SELECT 'invoices', count(*) FROM invoices UNION ALL
SELECT 'invoice_items', count(*) FROM invoice_items UNION ALL
SELECT 'devices', count(*) FROM devices UNION ALL
SELECT 'services', count(*) FROM services;

-- @id: Q-INT-002
-- @purpose: Utilisateurs par rôle, et rôles hors de la liste attendue (admin, employee, accountant).
-- @expected: uniquement les trois rôles attendus ; aucun rôle NULL.
SELECT COALESCE(role, '<NULL>') AS role, count(*) AS users,
       (role IS NULL OR role NOT IN ('admin','employee','accountant')) AS unexpected
FROM users GROUP BY role ORDER BY 1;

-- @id: Q-INT-003
-- @purpose: Utilisateurs avec des attributs obligatoires manquants (rôle, hash, prénom, nom, date de création).
-- @expected: 0 partout.
SELECT count(*) FILTER (WHERE role IS NULL) AS no_role,
       count(*) FILTER (WHERE "hashedPassword" IS NULL OR "hashedPassword" = '') AS no_password_hash,
       count(*) FILTER (WHERE "firstName" IS NULL OR "firstName" = '') AS no_first_name,
       count(*) FILTER (WHERE "lastName" IS NULL OR "lastName" = '') AS no_last_name,
       count(*) FILTER (WHERE "createdAt" IS NULL) AS no_created_at,
       count(*) FILTER (WHERE "isActive" IS NULL) AS null_is_active
FROM users;

-- @id: Q-INT-004
-- @purpose: Doublons d'e-mail insensibles à la casse (la contrainte UNIQUE est sensible à la casse).
-- @expected: 0. Une valeur > 0 prouve qu'une même personne peut avoir deux comptes (Alice@x.tn / alice@x.tn).
SELECT count(*) AS duplicate_groups, COALESCE(sum(n), 0) AS accounts_involved
FROM (SELECT count(*) AS n FROM users GROUP BY lower(email) HAVING count(*) > 1) d;

-- @id: Q-INT-005
-- @purpose: Format des identifiants utilisateur, et trous dans la séquence USR-NNN (cause de la collision count()+1).
-- @expected: identifiants au format USR-NNN ; tout trou rend `USR-{count()+1}` (main.py:235) susceptible de collision.
SELECT id, (id ~ '^USR-[0-9]{3,}$') AS well_formed,
       row_number() OVER (ORDER BY id) AS position,
       NULLIF(regexp_replace(id, '\D', '', 'g'), '')::int AS numeric_part
FROM users ORDER BY id;

-- @id: Q-INT-006
-- @purpose: Prochain identifiant que POST /api/users va générer (main.py:235) et s'il existe déjà.
-- @expected: l'identifiant généré doit être libre. Si already_taken = true, la création de compte échoue (violation de PK).
SELECT format('USR-%s', lpad((count(*)+1)::text, 3, '0')) AS id_generated_by_api,
       EXISTS (SELECT 1 FROM users u2 WHERE u2.id = format('USR-%s', lpad(((SELECT count(*) FROM users)+1)::text, 3, '0'))) AS already_taken
FROM users;

-- @id: Q-INT-007
-- @purpose: Jetons de réinitialisation présents en base, et jetons expirés non nettoyés.
-- @expected: 0 jeton expiré conservé. Valeurs jamais affichées — comptage uniquement.
SELECT count(*) FILTER (WHERE "resetToken" IS NOT NULL) AS tokens_stored,
       count(*) FILTER (WHERE "resetToken" IS NOT NULL AND ("resetTokenExpiry" IS NULL OR "resetTokenExpiry" < now() AT TIME ZONE 'UTC')) AS tokens_expired_or_without_expiry
FROM users;

-- @id: Q-INT-008
-- @purpose: Comptes inactifs ou non vérifiés (pour le test OBS-011 : un compte inactif peut-il se connecter ?).
-- @expected: inventaire seulement.
SELECT "isActive" AS is_active, "isVerified" AS is_verified, count(*) FROM users GROUP BY 1, 2 ORDER BY 1, 2;

-- @id: Q-INT-009
-- @purpose: Orphelins logiques entre team_members et users (aucune FK ne les relie).
-- @expected: chaque membre d'équipe correspond à un compte, et inversement — à confirmer comme règle métier en phase 9.
SELECT
  (SELECT count(*) FROM team_members tm WHERE NOT EXISTS (SELECT 1 FROM users u WHERE lower(u.email)=lower(tm.email))) AS members_without_account,
  (SELECT count(*) FROM users u WHERE u.role='employee' AND NOT EXISTS (SELECT 1 FROM team_members tm WHERE lower(tm.email)=lower(u.email))) AS employees_without_member_profile;

-- @id: Q-INT-010
-- @purpose: Orphelins sur les clés étrangères déclarées (ne doit jamais arriver si la FK existe réellement en base).
-- @expected: 0 partout. Une valeur > 0 prouverait que la FK est absente du schéma réel.
SELECT
  (SELECT count(*) FROM payslips p WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id=p.employee_id)) AS payslips_orphan_employee,
  (SELECT count(*) FROM leave_requests l WHERE l.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id=l.employee_id)) AS leaves_orphan_employee,
  (SELECT count(*) FROM leave_requests l WHERE l.valide_par_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id=l.valide_par_id)) AS leaves_orphan_validator,
  (SELECT count(*) FROM invoices i WHERE NOT EXISTS (SELECT 1 FROM clients c WHERE c.id=i.client_id)) AS invoices_orphan_client,
  (SELECT count(*) FROM invoices i WHERE i.cree_par_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id=i.cree_par_id)) AS invoices_orphan_creator,
  (SELECT count(*) FROM invoice_items it WHERE NOT EXISTS (SELECT 1 FROM invoices i WHERE i.id=it.invoice_id)) AS items_orphan_invoice;

-- @id: Q-INT-011
-- @purpose: Factures dans un état incohérent : sans statut, sans montant, sans créateur, sans ligne, échéance avant émission.
-- @expected: 0 partout.
SELECT count(*) FILTER (WHERE statut IS NULL) AS no_status,
       count(*) FILTER (WHERE montant_ht IS NULL OR montant_ttc IS NULL) AS no_amount,
       count(*) FILTER (WHERE cree_par_id IS NULL) AS no_creator,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM invoice_items it WHERE it.invoice_id=i.id)) AS no_items,
       count(*) FILTER (WHERE date_echeance < date_emission) AS due_before_issue,
       count(*) FILTER (WHERE montant_ht < 0 OR montant_ttc < 0) AS negative_amount,
       count(*) FILTER (WHERE montant_ttc < montant_ht) AS ttc_below_ht
FROM invoices i;

-- @id: Q-INT-012
-- @purpose: Montants stockés incohérents avec la somme des lignes (montant_ht/ttc sont des valeurs dérivées).
-- @expected: 0 facture dont le montant diffère de la somme recalculée.
SELECT i.id, i.numero,
       i.montant_ht AS stored_ht, round(sum(it.quantite*it.prix_unitaire), 2) AS computed_ht,
       i.montant_ttc AS stored_ttc, round(sum(it.quantite*it.prix_unitaire*(1+it.taux_tva/100)), 2) AS computed_ttc
FROM invoices i JOIN invoice_items it ON it.invoice_id=i.id
GROUP BY i.id
HAVING i.montant_ht IS DISTINCT FROM round(sum(it.quantite*it.prix_unitaire), 2)
    OR i.montant_ttc IS DISTINCT FROM round(sum(it.quantite*it.prix_unitaire*(1+it.taux_tva/100)), 2);

-- @id: Q-INT-013
-- @purpose: Lignes de facture invalides : quantité nulle ou négative, prix négatif, taux de TVA hors plage.
-- @expected: 0 partout.
SELECT count(*) FILTER (WHERE quantite IS NULL OR quantite <= 0) AS bad_quantity,
       count(*) FILTER (WHERE prix_unitaire < 0) AS negative_price,
       count(*) FILTER (WHERE taux_tva IS NULL OR taux_tva < 0 OR taux_tva > 100) AS bad_vat_rate
FROM invoice_items;

-- @id: Q-INT-014
-- @purpose: Numéros de facture : formats coexistants et trous dans la numérotation par année (ticket #38).
-- @expected: un seul format ; numérotation continue.
SELECT CASE WHEN numero ~ '^FA-[0-9]{4}-[0-9]{4}$' THEN 'FA-YYYY-NNNN'
            WHEN numero ~ '^INV-[0-9]{4}-[0-9]+$' THEN 'INV-YYYY-NNN'
            ELSE 'other' END AS format, count(*)
FROM invoices GROUP BY 1;

-- @id: Q-INT-015
-- @purpose: Congés incohérents : sans employé, date de fin avant date de début, décision sans valideur.
-- @expected: 0 partout.
SELECT count(*) FILTER (WHERE employee_id IS NULL) AS no_employee,
       count(*) FILTER (WHERE date_fin < date_debut) AS end_before_start,
       count(*) FILTER (WHERE statut IN ('APPROUVE','REFUSE') AND valide_par_id IS NULL) AS decided_without_validator,
       count(*) FILTER (WHERE valide_par_id IS NOT NULL AND valide_par_id = employee_id) AS self_validated
FROM leave_requests;

-- @id: Q-INT-016
-- @purpose: Congés qui se chevauchent pour un même employé.
-- @expected: 0 (aucune contrainte d'exclusion n'empêche le chevauchement).
SELECT a.employee_id, a.id AS leave_a, b.id AS leave_b
FROM leave_requests a JOIN leave_requests b
  ON a.employee_id=b.employee_id AND a.id < b.id
 AND daterange(a.date_debut, a.date_fin, '[]') && daterange(b.date_debut, b.date_fin, '[]');

-- @id: Q-INT-017
-- @purpose: Bulletins de paie invalides : net supérieur au brut, montants négatifs.
-- @expected: 0 partout.
SELECT count(*) FILTER (WHERE montant_net > montant_brut) AS net_above_gross,
       count(*) FILTER (WHERE montant_brut < 0 OR montant_net < 0) AS negative
FROM payslips;

-- @id: Q-INT-018
-- @purpose: Appareils : statuts hors liste, numéros de série dupliqués ou manquants, prix invalides.
-- @expected: statuts dans {Available, Sold, ...} ; numéros de série uniques.
SELECT COALESCE(status,'<NULL>') AS status, count(*),
       count(*) FILTER (WHERE "serialNumber" IS NULL OR "serialNumber"='') AS no_serial,
       count(*) FILTER (WHERE price IS NULL OR price < 0) AS bad_price
FROM devices GROUP BY status;

-- @id: Q-INT-019
-- @purpose: Numéros de série d'appareils dupliqués (aucune contrainte UNIQUE déclarée).
-- @expected: 0.
SELECT "serialNumber", count(*) FROM devices WHERE "serialNumber" IS NOT NULL GROUP BY 1 HAVING count(*) > 1;

-- @id: Q-INT-020
-- @purpose: Clients en doublon (même nom, insensible à la casse) — aucune contrainte UNIQUE déclarée.
-- @expected: 0.
SELECT lower(nom) AS normalised_name, count(*) FROM clients GROUP BY 1 HAVING count(*) > 1;
