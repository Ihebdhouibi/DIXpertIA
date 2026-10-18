import { defineMessages } from '../define';

/** invoices: the invoices screen and its dialogs. See ../define.ts; keys start with "invoices.". */
export default defineMessages('invoices', {
  // The screen
  'invoices.title': { fr: 'Factures', en: 'Invoices' },
  'invoices.intro': {
    fr: 'Gérez et suivez la facturation de tous vos projets.',
    en: 'Manage and track billing across all projects.',
  },
  'invoices.new': { fr: 'Nouvelle facture', en: 'New invoice' },
  'invoices.noun': { fr: 'factures', en: 'invoices' },
  'invoices.loading': { fr: 'Chargement des factures…', en: 'Loading invoices…' },
  'invoices.couldNotLoad': { fr: 'Impossible de charger les factures', en: 'Could not load invoices' },
  'invoices.retry': { fr: 'Réessayer', en: 'Retry' },
  'invoices.cancel': { fr: 'Annuler', en: 'Cancel' },
  'invoices.noneMatch': { fr: 'Aucune facture ne correspond', en: 'No invoices match' },
  'invoices.noneYet': { fr: 'Aucune facture pour le moment', en: 'No invoices yet' },
  'invoices.noneMatchHint': {
    fr: 'Essayez un autre mois, client ou statut.',
    en: 'Try another month, client or status.',
  },
  'invoices.refused': { fr: 'Refusé par le serveur', en: 'Refused by the server' },

  // Direction
  'invoices.direction': { fr: 'Sens', en: 'Direction' },
  'invoices.direction.incoming': { fr: 'Reçue', en: 'Incoming' },
  'invoices.direction.outgoing': { fr: 'Émise', en: 'Outgoing' },
  'invoices.direction.both': { fr: 'Émises et reçues', en: 'Incoming and outgoing' },
  'invoices.direction.outgoingLong': { fr: 'Émises (nous facturons)', en: 'Outgoing (we bill)' },
  'invoices.direction.incomingLong': { fr: 'Reçues (nous sommes facturés)', en: 'Incoming (we are billed)' },

  // Filters
  'invoices.filter.month': { fr: 'Mois', en: 'Month' },
  'invoices.filter.client': { fr: 'Client', en: 'Client' },
  'invoices.filter.allClients': { fr: 'Tous les clients', en: 'All clients' },
  'invoices.filter.status': { fr: 'Statut', en: 'Status' },
  'invoices.filter.allStatuses': { fr: 'Tous les statuts', en: 'All statuses' },
  'invoices.filter.verification': { fr: 'Vérification', en: 'Verification' },
  'invoices.filter.anyStage': { fr: 'Toutes les étapes', en: 'Any stage' },
  'invoices.filter.all': { fr: 'Toutes', en: 'All' },
  'invoices.filter.clear': { fr: 'Effacer les filtres', en: 'Clear filters' },
  'invoices.books': { fr: 'Comptabilité', en: 'Books' },

  // Table
  'invoices.col.invoice': { fr: 'Facture', en: 'Invoice' },
  'invoices.col.counterparty': { fr: 'Client / fournisseur', en: 'Client / supplier' },
  'invoices.col.amount': { fr: 'Montant', en: 'Amount' },
  'invoices.col.dates': { fr: 'Émission / échéance', en: 'Issued / due' },
  'invoices.col.status': { fr: 'Statut', en: 'Status' },
  'invoices.col.actions': { fr: 'Actions', en: 'Actions' },
  'invoices.due': { fr: 'échéance {date}', en: 'due {date}' },
  'invoices.selectAll': {
    fr: 'Sélectionner les factures de cette page pouvant avancer',
    en: 'Select every invoice on this page that can move',
  },
  'invoices.selectOne': { fr: 'Sélectionner la facture {ref}', en: 'Select invoice {ref}' },
  'invoices.verify': { fr: 'Vérifier', en: 'Verify' },
  'invoices.verifyOne': { fr: 'Vérifier la facture {ref}', en: 'Verify invoice {ref}' },
  'invoices.stepOne': { fr: '{action} : facture {ref}', en: '{action}: invoice {ref}' },
  'invoices.downloadOne': { fr: 'Télécharger la facture {ref}', en: 'Download invoice {ref}' },

  // Processing actions (invoiceStatus.ts)
  'invoices.action.markProcessed': { fr: 'Marquer traitée', en: 'Mark processed' },
  'invoices.action.markCompleted': { fr: 'Marquer finalisée', en: 'Mark completed' },
  'invoices.action.process': { fr: 'Traiter', en: 'Process' },
  'invoices.action.complete': { fr: 'Finaliser', en: 'Complete' },

  // Bulk selection
  'invoices.selection': { fr: 'Factures sélectionnées', en: 'Selected invoices' },
  'invoices.selectedCount': {
    fr: { one: '{count} sélectionnée', other: '{count} sélectionnées' },
    en: { one: '{count} selected', other: '{count} selected' },
  },
  'invoices.clearSelection': { fr: 'Désélectionner', en: 'Clear selection' },
  'invoices.moved.Processed': {
    fr: { one: '{count} facture traitée.', other: '{count} factures traitées.' },
    en: { one: '{count} invoice processed.', other: '{count} invoices processed.' },
  },
  'invoices.moved.Completed': {
    fr: { one: '{count} facture finalisée.', other: '{count} factures finalisées.' },
    en: { one: '{count} invoice completed.', other: '{count} invoices completed.' },
  },
  'invoices.notMoved': {
    fr: { one: "{count} facture n'a pas avancé : {reason}", other: "{count} factures n'ont pas avancé : {reason}" },
    en: { one: '{count} invoice not moved: {reason}', other: '{count} invoices not moved: {reason}' },
  },

  // Download
  'invoices.fileName': { fr: 'Facture_{ref}.pdf', en: 'Invoice_{ref}.pdf' },
  'invoices.downloaded': { fr: 'Facture {ref} téléchargée.', en: 'Invoice {ref} downloaded.' },
  'invoices.downloadFailed': { fr: 'Échec du téléchargement : {error}', en: 'Download failed: {error}' },
  'invoices.networkError': { fr: 'erreur réseau', en: 'network error' },
  'invoices.download': { fr: 'Télécharger', en: 'Download' },

  // Verification and status changes, as toasts
  'invoices.done.approved': { fr: 'Facture {ref} approuvée.', en: 'Invoice {ref} approved.' },
  'invoices.done.sent': { fr: 'Facture {ref} marquée comme envoyée.', en: 'Invoice {ref} marked as sent.' },
  'invoices.done.submitted': {
    fr: 'Facture {ref} soumise à vérification.',
    en: 'Invoice {ref} submitted for verification.',
  },
  'invoices.done.rejected': {
    fr: "Facture {ref} renvoyée à l'administrateur.",
    en: 'Invoice {ref} sent back to the admin.',
  },
  'invoices.done.paid': { fr: 'Facture {ref} marquée comme payée.', en: 'Invoice {ref} marked as paid.' },
  'invoices.done.cancelled': { fr: 'Facture {ref} annulée.', en: 'Invoice {ref} cancelled.' },
  'invoices.done.updated': { fr: 'Facture {ref} modifiée.', en: 'Invoice {ref} updated.' },
  'invoices.done.created': {
    fr: 'Facture {ref} créée en brouillon.',
    en: 'Invoice {ref} created as a draft.',
  },

  // Confirmations
  'invoices.approve.title': { fr: 'Approuver {ref} ?', en: 'Approve {ref}?' },
  'invoices.approve.message': {
    fr: "Elle reçoit son numéro légal et la date du jour, et peut ensuite être envoyée. Action irréversible.",
    en: "It gets its legal number and today's date, and can then be sent. This cannot be undone.",
  },
  'invoices.approve': { fr: 'Approuver', en: 'Approve' },
  'invoices.send.title': { fr: 'Marquer {ref} comme envoyée ?', en: 'Mark {ref} as sent?' },
  'invoices.send.message': {
    fr: 'À faire une fois le PDF transmis au client. La facture devient alors définitive et peut être comptabilisée.',
    en: 'Do it once the PDF has gone to the client. The invoice is then final and the books can take it.',
  },
  'invoices.markSent': { fr: 'Marquer envoyée', en: 'Mark as sent' },

  // Invoice detail
  'invoices.detail.title': { fr: 'Facture {ref}', en: 'Invoice {ref}' },
  'invoices.edit': { fr: 'Modifier', en: 'Edit' },
  'invoices.submit': { fr: 'Soumettre à vérification', en: 'Submit for verification' },
  'invoices.reject': { fr: 'Rejeter', en: 'Reject' },
  'invoices.markPaid': { fr: 'Marquer payée', en: 'Mark as paid' },
  'invoices.cancelInvoice': { fr: 'Annuler la facture', en: 'Cancel invoice' },
  'invoices.summary': { fr: 'Récapitulatif', en: 'Summary' },
  'invoices.exclVat': { fr: 'Total HT', en: 'Excl. VAT' },
  'invoices.vat': { fr: 'TVA', en: 'VAT' },
  'invoices.inclVat': { fr: 'Total TTC', en: 'Total incl. VAT' },
  'invoices.issued': { fr: 'Émission', en: 'Issued' },
  'invoices.dueLabel': { fr: 'Échéance', en: 'Due' },
  'invoices.paid': { fr: 'Payée le', en: 'Paid' },
  'invoices.cancelledPrefix': { fr: 'Annulée :', en: 'Cancelled:' },
  'invoices.supplier': { fr: 'Fournisseur', en: 'Supplier' },
  'invoices.client': { fr: 'Client', en: 'Client' },
  'invoices.noAddress': { fr: 'Aucune adresse enregistrée.', en: 'No address on file.' },
  'invoices.supplierReference': { fr: 'Référence fournisseur', en: 'Supplier reference' },

  // Create and edit
  'invoices.create.title': { fr: 'Nouvelle facture', en: 'Create new invoice' },
  'invoices.create.description': {
    fr: "Créée en brouillon. Le numéro et la date d'émission sont attribués par le serveur.",
    en: 'Created as a draft. The number and the issue date are assigned by the server.',
  },
  'invoices.create.submit': { fr: 'Créer la facture', en: 'Create invoice' },
  'invoices.create.failed': { fr: 'Impossible de créer la facture.', en: 'Could not create the invoice.' },
  'invoices.create.noClients': {
    fr: "Aucun client pour le moment. Ajoutez-en un avant d'émettre une facture.",
    en: 'No clients yet. Add one before issuing an invoice.',
  },
  'invoices.create.chooseClient': { fr: 'Choisir un client', en: 'Choose a client' },
  'invoices.error.chooseClient': { fr: 'Choisissez un client.', en: 'Choose a client.' },
  'invoices.error.chooseDueDate': { fr: "Choisissez une date d'échéance.", en: 'Choose a due date.' },
  'invoices.error.dueInPast': {
    fr: "La date d'échéance ne peut pas être passée.",
    en: 'The due date cannot be in the past.',
  },
  'invoices.dueDate': { fr: "Date d'échéance", en: 'Due date' },
  'invoices.edit.title': { fr: 'Modifier {ref}', en: 'Edit {ref}' },
  'invoices.edit.description': {
    fr: "Seul un brouillon peut être corrigé. Le numéro, la date d'émission et le client restent inchangés.",
    en: 'Only a draft can be corrected. The number, issue date and client stay as they are.',
  },
  'invoices.edit.save': { fr: 'Enregistrer', en: 'Save changes' },
  'invoices.edit.failed': { fr: "Impossible d'enregistrer la facture.", en: 'Could not save the invoice.' },

  // Lines
  'invoices.lines': { fr: 'Lignes', en: 'Lines' },
  'invoices.line.description': { fr: 'Désignation', en: 'Description' },
  'invoices.line.unitPrice': { fr: 'Prix unitaire', en: 'Unit price' },
  'invoices.line.descriptionLabel': { fr: 'Ligne {n}, désignation', en: 'Line {n} description' },
  'invoices.line.quantityLabel': { fr: 'Ligne {n}, quantité', en: 'Line {n} quantity' },
  'invoices.line.unitPriceLabel': {
    fr: 'Ligne {n}, prix unitaire HT en TND',
    en: 'Line {n} unit price, TND excl. VAT',
  },
  'invoices.line.vatLabel': { fr: 'Ligne {n}, taux de TVA', en: 'Line {n} VAT rate' },
  'invoices.line.removeLabel': { fr: 'Supprimer la ligne {n}', en: 'Remove line {n}' },
  'invoices.line.remove': { fr: 'Supprimer la ligne', en: 'Remove line' },
  'invoices.line.add': { fr: 'Ajouter une ligne', en: 'Add a line' },
  'invoices.line.needOne': { fr: 'Ajoutez au moins une ligne.', en: 'Add at least one line.' },
  'invoices.line.needDescription': { fr: 'Ligne {n} : désignation manquante.', en: 'Line {n} needs a description.' },
  'invoices.line.needQuantity': {
    fr: 'Ligne {n} : la quantité doit être supérieure à zéro.',
    en: 'Line {n}: the quantity must be above zero.',
  },
  'invoices.line.needUnitPrice': { fr: 'Ligne {n} : prix unitaire manquant.', en: 'Line {n} needs a unit price.' },
  'invoices.totalExclVat': { fr: 'Total HT', en: 'Total excl. VAT' },
  'invoices.totalInclVat': { fr: 'Total TTC', en: 'Total incl. VAT' },

  // History
  'invoices.history': { fr: 'Historique', en: 'History' },
  'invoices.history.loading': { fr: "Chargement de l'historique…", en: 'Loading the history…' },
  'invoices.history.failed': { fr: "Impossible de charger l'historique.", en: 'Could not load the history.' },
  'invoices.history.empty': {
    fr: "Rien d'enregistré pour le moment. Les étapes sont enregistrées depuis la mise en place du journal d'audit.",
    en: 'Nothing recorded yet. Steps are recorded since the audit trail was introduced.',
  },

  // PDF preview
  'invoices.pdf.heading': { fr: 'Document envoyé au client', en: 'Document sent to the client' },
  'invoices.pdf.open': { fr: 'Ouvrir le PDF', en: 'Open PDF' },
  'invoices.pdf.page': {
    fr: 'Facture {ref}, page {page} sur {count}',
    en: 'Invoice {ref}, page {page} of {count}',
  },
  'invoices.pdf.loading': { fr: 'Chargement du PDF…', en: 'Loading the PDF…' },
  'invoices.pdf.failed': { fr: "Le PDF n'a pas pu être généré.", en: 'The PDF could not be generated.' },
  'invoices.pdf.couldNotLoad': { fr: 'Impossible de charger le PDF.', en: 'Could not load the PDF.' },
  'invoices.pdf.couldNotDraw': { fr: "Impossible d'afficher le PDF.", en: 'Could not draw the PDF.' },

  // Verification panel and rejection
  'invoices.review.title': { fr: 'Vérification', en: 'Verification' },
  'invoices.review.submitted': { fr: 'Soumise à vérification', en: 'Submitted for verification' },
  'invoices.review.approved': { fr: 'Approuvée', en: 'Approved' },
  'invoices.review.rejected': { fr: 'Rejetée', en: 'Rejected' },
  'invoices.review.toCorrect': { fr: 'À corriger, selon {actor}', en: 'To correct, from {actor}' },
  'invoices.review.theAccountant': { fr: 'le comptable', en: 'the accountant' },
  'invoices.review.numberedBefore': {
    fr: 'Numérotée avant la mise en place de la vérification.',
    en: 'Numbered before verification existed.',
  },
  'invoices.review.notSubmitted': {
    fr: "Pas encore soumise. Le numéro légal est attribué à l'approbation du comptable.",
    en: 'Not submitted yet. The legal number is assigned when the accountant approves it.',
  },
  'invoices.reject.title': { fr: 'Rejeter {ref}', en: 'Reject {ref}' },
  'invoices.reject.description': {
    fr: "L'administrateur voit ce commentaire, corrige le brouillon et le soumet à nouveau.",
    en: 'The admin sees this comment, corrects the draft and submits it again.',
  },
  'invoices.reject.field': { fr: 'À corriger', en: 'What should be corrected' },
  'invoices.reject.placeholder': {
    fr: 'ex. La formation est facturée à 7 % de TVA, pas 19 %.',
    en: 'e.g. Training is billed at 7% VAT, not 19%.',
  },
  'invoices.reject.required': {
    fr: "Indiquez ce que l'administrateur doit corriger.",
    en: 'Say what the admin should correct.',
  },
  'invoices.reject.failed': { fr: 'Impossible de rejeter la facture.', en: 'Could not reject the invoice.' },

  // Pay and cancel
  'invoices.pay.title': { fr: 'Marquer {ref} comme payée', en: 'Mark {ref} as paid' },
  'invoices.pay.description': {
    fr: 'Payée intégralement à la date ci-dessous. Action irréversible.',
    en: 'Paid in full on the date below. This cannot be undone.',
  },
  'invoices.pay.date': { fr: 'Date de paiement', en: 'Payment date' },
  'invoices.pay.dateHint': {
    fr: "Entre la date d'émission et aujourd'hui.",
    en: 'Between the issue date and today.',
  },
  'invoices.pay.required': {
    fr: 'Saisissez la date de réception du paiement.',
    en: 'Enter the date the payment arrived.',
  },
  'invoices.pay.failed': { fr: "Impossible d'enregistrer le paiement.", en: 'Could not record the payment.' },
  'invoices.cancel.title': { fr: 'Annuler {ref}', en: 'Cancel {ref}' },
  'invoices.cancel.numbered': {
    fr: 'Elle garde son numéro dans la série, marquée annulée. Les comptables sont prévenus pour comptabiliser un avoir. Action irréversible.',
    en: 'It keeps its number in the series, marked cancelled. The accountants are told, to book a credit note. This cannot be undone.',
  },
  'invoices.cancel.draft': {
    fr: "Le brouillon n'a pas de numéro légal : rien ne reste dans la série. Action irréversible.",
    en: 'The draft has no legal number, so nothing is left in the series. This cannot be undone.',
  },
  'invoices.cancel.keep': { fr: 'Conserver', en: 'Keep it' },
  'invoices.cancel.reason': { fr: 'Motif', en: 'Reason' },
  'invoices.cancel.placeholder': {
    fr: 'ex. Le client a retiré sa commande.',
    en: 'e.g. The client withdrew the order.',
  },
  'invoices.cancel.required': {
    fr: "Indiquez pourquoi la facture est annulée.",
    en: 'Say why the invoice is cancelled.',
  },
  'invoices.cancel.failed': { fr: "Impossible d'annuler la facture.", en: 'Could not cancel the invoice.' },

  // Clients (#192)
  'invoices.clients.title': { fr: 'Clients', en: 'Clients' },
  'invoices.clients.intro': {
    fr: 'Les clients à facturer, et la langue dans laquelle leurs factures sont imprimées.',
    en: 'The clients you invoice, and the language their invoices print in.',
  },
  'invoices.clients.new': { fr: 'Nouveau client', en: 'New client' },
  'invoices.clients.edit': { fr: 'Modifier', en: 'Edit' },
  'invoices.clients.editLabel': { fr: 'Modifier {name}', en: 'Edit {name}' },
  'invoices.clients.search': { fr: 'Rechercher un client', en: 'Search clients' },
  'invoices.clients.searchPlaceholder': { fr: 'Nom ou e-mail…', en: 'Name or email...' },
  'invoices.clients.col.name': { fr: 'Client', en: 'Client' },
  'invoices.clients.col.contact': { fr: 'Contact', en: 'Contact' },
  'invoices.clients.col.language': { fr: 'Langue des factures', en: 'Invoice language' },
  'invoices.clients.col.actions': { fr: 'Actions', en: 'Actions' },
  'invoices.clients.count': {
    fr: { one: '{count} client', other: '{count} clients' },
    en: { one: '{count} client', other: '{count} clients' },
  },
  'invoices.clients.empty': { fr: 'Aucun client pour le moment', en: 'No clients yet' },
  'invoices.clients.emptyHint': {
    fr: 'Ajoutez un client pour pouvoir lui adresser une facture.',
    en: 'Add a client to be able to invoice them.',
  },
  'invoices.clients.noMatch': { fr: 'Aucun client ne correspond à « {query} »', en: 'No client matches "{query}"' },
  'invoices.clients.noContact': { fr: 'Aucun contact', en: 'No contact' },
  'invoices.clients.lang.fr': { fr: 'Français', en: 'French' },
  'invoices.clients.lang.en': { fr: 'Anglais', en: 'English' },
  'invoices.clients.form.addTitle': { fr: 'Nouveau client', en: 'New client' },
  'invoices.clients.form.editTitle': { fr: 'Modifier le client', en: 'Edit client' },
  'invoices.clients.form.name': { fr: 'Nom', en: 'Name' },
  'invoices.clients.form.email': { fr: 'E-mail', en: 'Email' },
  'invoices.clients.form.phone': { fr: 'Téléphone', en: 'Phone' },
  'invoices.clients.form.address': { fr: 'Adresse', en: 'Address' },
  'invoices.clients.form.addressHint': {
    fr: 'Imprimée sur les factures, telle quelle, ligne par ligne.',
    en: 'Printed on invoices as is, line by line.',
  },
  'invoices.clients.form.language': { fr: 'Langue des factures', en: 'Invoice language' },
  'invoices.clients.form.languageHint': {
    fr: "Les factures de ce client sont imprimées dans cette langue, quel que soit l'utilisateur qui les télécharge.",
    en: 'Invoices for this client print in this language, whoever downloads them.',
  },
  'invoices.clients.form.nameRequired': { fr: 'Le nom du client est obligatoire.', en: 'The client name is required.' },
  'invoices.clients.form.emailInvalid': { fr: "L'adresse e-mail n'est pas valide.", en: 'The email address is not valid.' },
  'invoices.clients.form.save': { fr: 'Enregistrer', en: 'Save' },
  'invoices.clients.form.create': { fr: 'Créer le client', en: 'Create client' },
  'invoices.clients.form.cancel': { fr: 'Annuler', en: 'Cancel' },
  'invoices.clients.created': { fr: 'Client « {name} » créé.', en: 'Client "{name}" created.' },
  'invoices.clients.updated': { fr: 'Client « {name} » mis à jour.', en: 'Client "{name}" updated.' },
  'invoices.clients.couldNotSave': { fr: "Impossible d'enregistrer le client.", en: 'Could not save the client.' },
  'invoices.clients.loading': { fr: 'Chargement des clients…', en: 'Loading clients...' },
});
