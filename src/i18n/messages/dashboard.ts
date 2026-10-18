import { defineMessages } from '../define';

/** dashboard: the dashboard screen. See ../define.ts; keys start with "dashboard.". */
export default defineMessages('dashboard', {
  'dashboard.welcome': { fr: 'Bonjour, {name}', en: 'Welcome back, {name}' },
  'dashboard.intro.admin': {
    fr: "Les factures en attente de comptabilisation, les congés à décider et votre équipe d'un coup d'œil.",
    en: 'Invoices waiting on the books, leave to decide and your team at a glance.',
  },
  'dashboard.intro.accountant': {
    fr: 'Où en sont les factures dans la comptabilité, et ce qui vous attend.',
    en: 'Where the invoices stand in the books, and what is waiting for you.',
  },
  'dashboard.intro.employee': {
    fr: 'Vos demandes de congé, votre prochain congé et votre dernier bulletin de paie.',
    en: 'Your leave requests, your next time off and your latest payslip.',
  },
  'dashboard.figuresNotLoaded': {
    fr: "Certains chiffres n'ont pas pu être chargés : {error}",
    en: 'Some figures could not be loaded: {error}',
  },
  'dashboard.open': { fr: 'Ouvrir', en: 'Open' },
  'dashboard.loading': { fr: 'Chargement…', en: 'Loading…' },

  'dashboard.metric.awaitingBooking': { fr: 'À comptabiliser', en: 'Awaiting booking' },
  'dashboard.metric.awaitingBookingHint': {
    fr: { one: 'facture en attente', other: 'factures en attente' },
    en: { one: 'invoice in Pending', other: 'invoices in Pending' },
  },
  'dashboard.metric.clientInvoices': { fr: 'Factures clients', en: 'Client invoices' },
  'dashboard.metric.supplierBills': { fr: 'Factures fournisseurs', en: 'Supplier bills' },
  'dashboard.metric.leaveToDecide': { fr: 'Congés à décider', en: 'Leave to decide' },
  'dashboard.metric.leaveToDecideHint': {
    fr: { one: 'demande en attente', other: 'demandes en attente' },
    en: { one: 'pending request', other: 'pending requests' },
  },
  'dashboard.metric.activeTeam': { fr: 'Équipe active', en: 'Active team' },
  'dashboard.metric.activeTeamHint': {
    fr: { one: '{count} employé au total', other: '{count} employés au total' },
    en: { one: '{count} employee in total', other: '{count} employees in total' },
  },
  'dashboard.metric.toComplete': { fr: 'À finaliser', en: 'To complete' },
  'dashboard.metric.toCompleteHint': {
    fr: { one: 'facture traitée', other: 'factures traitées' },
    en: { one: 'invoice in Processed', other: 'invoices in Processed' },
  },
  'dashboard.metric.completed': { fr: 'Finalisées', en: 'Completed' },
  'dashboard.metric.completedHint': { fr: 'prêtes pour la clôture du mois', en: 'ready for the month close' },
  'dashboard.metric.pendingRequests': { fr: 'Demandes en attente', en: 'Pending requests' },
  'dashboard.metric.pendingRequestsHint': { fr: 'en attente de décision', en: 'waiting for a decision' },
  'dashboard.metric.nextLeave': { fr: 'Prochain congé', en: 'Next leave' },
  'dashboard.metric.nextLeaveHint': {
    fr: { one: '{type} · {count} jour', other: '{type} · {count} jours' },
    en: { one: '{type} · {count} day', other: '{type} · {count} days' },
  },
  'dashboard.metric.nothingApproved': { fr: 'aucun congé approuvé à venir', en: 'nothing approved ahead' },
  'dashboard.metric.latestPayslip': { fr: 'Dernier bulletin', en: 'Latest payslip' },
  'dashboard.metric.net': { fr: 'net {amount}', en: 'net {amount}' },
  'dashboard.metric.noneIssued': { fr: 'aucun émis pour le moment', en: 'none issued yet' },
  'dashboard.metric.unread': { fr: 'Non lues', en: 'Unread' },
  'dashboard.metric.unreadHint': {
    fr: { one: 'notification', other: 'notifications' },
    en: { one: 'notification', other: 'notifications' },
  },
  'dashboard.none': { fr: 'Aucun', en: 'None' },

  'dashboard.byProcessing': { fr: 'Factures par étape de traitement', en: 'Invoices by processing state' },
  'dashboard.invoiceCount': {
    fr: { one: '{count} facture', other: '{count} factures' },
    en: { one: '{count} invoice', other: '{count} invoices' },
  },
  'dashboard.noInvoices': { fr: 'Aucune facture pour le moment.', en: 'No invoices yet.' },
  'dashboard.byStatus': { fr: 'Factures par statut', en: 'Invoices by status' },
  'dashboard.quickActions': { fr: 'Actions rapides', en: 'Quick actions' },
  'dashboard.reviewLeave': { fr: 'Examiner les demandes de congé', en: 'Review leave requests' },
  'dashboard.createInvoice': { fr: 'Créer une facture', en: 'Create an invoice' },
  'dashboard.yourLeave': { fr: 'Vos congés', en: 'Your leave' },
  'dashboard.balance': { fr: 'Solde', en: 'Balance' },
  'dashboard.balanceUnavailable': {
    fr: 'Les soldes de congés ne sont pas encore disponibles.',
    en: 'Leave balances are not available yet.',
  },
  'dashboard.nextApprovedLeave': { fr: 'Prochain congé approuvé', en: 'Next approved leave' },
  'dashboard.noneScheduled': { fr: 'Aucun de prévu.', en: 'None scheduled.' },
  'dashboard.recentActivity': { fr: 'Activité récente', en: 'Recent activity' },
  'dashboard.viewAll': { fr: 'Tout voir', en: 'View all' },
  'dashboard.noActivity': { fr: 'Aucune activité récente.', en: 'No recent activity.' },
  'dashboard.unreadPrefix': { fr: 'Non lue : ', en: 'Unread: ' },
});
