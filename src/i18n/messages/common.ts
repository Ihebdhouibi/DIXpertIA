import { defineMessages } from '../define';

/** common: the app shell and words used everywhere. See ../define.ts; keys start with "common.". */
export default defineMessages('common', {
  'common.language': { fr: 'Langue', en: 'Language' },
  'common.sessionExpired': {
    fr: 'Votre session a expiré. Veuillez vous reconnecter.',
    en: 'Your session has expired. Please sign in again.',
  },
  'common.requestFailed': { fr: 'La requête a échoué ({status})', en: 'Request failed ({status})' },
  'common.couldNotLoad': { fr: 'Impossible de charger les données', en: 'Could not load data' },
  'common.couldNotUpdateNotifications': {
    fr: 'Impossible de mettre à jour les notifications',
    en: 'Could not update notifications',
  },
  'common.couldNotSubmitLeave': {
    fr: "Impossible d'envoyer la demande de congé",
    en: 'Could not submit the leave request',
  },
  'common.couldNotApprove': { fr: "Impossible d'approuver la demande", en: 'Could not approve the request' },
  'common.couldNotReject': { fr: 'Impossible de refuser la demande', en: 'Could not reject the request' },
  'common.accessDenied': { fr: 'Accès refusé', en: 'Access denied' },
  'common.noPermissionLeave': {
    fr: "Vous n'avez pas l'autorisation de consulter les demandes de congé.",
    en: 'You do not have permission to view leave requests.',
  },
  'common.noPermissionPage': {
    fr: "Vous n'avez pas l'autorisation de consulter cette page.",
    en: 'You do not have permission to view this page.',
  },
  'common.unknownScreen': { fr: "Cet écran n'existe pas", en: 'This screen does not exist' },
  'common.unknownScreenHint': {
    fr: 'Le lien suivi mène à un écran inconnu. Revenez au tableau de bord.',
    en: 'The link you followed leads to an unknown screen. Go back to the dashboard.',
  },
  'common.backToDashboard': { fr: 'Retour au tableau de bord', en: 'Back to the dashboard' },
  'common.signingIn': { fr: 'Connexion en cours…', en: 'Signing you in…' },
  'common.someDataNotLoaded': {
    fr: "Certaines données n'ont pas pu être chargées",
    en: 'Some data could not be loaded',
  },
  'common.retry': { fr: 'Réessayer', en: 'Retry' },

  // Business statuses, as StatusBadge shows them. The key is the API's English
  // value, which also picks the badge's colour. French agrees with the noun it
  // describes: a facture or a demande (feminine), a compte (masculine).
  'common.status.Draft': { fr: 'Brouillon', en: 'Draft' },
  'common.status.Sent': { fr: 'Envoyée', en: 'Sent' },
  'common.status.Paid': { fr: 'Payée', en: 'Paid' },
  'common.status.Overdue': { fr: 'En retard', en: 'Overdue' },
  'common.status.Cancelled': { fr: 'Annulée', en: 'Cancelled' },
  'common.status.Pending': { fr: 'En attente', en: 'Pending' },
  'common.status.Approved': { fr: 'Approuvée', en: 'Approved' },
  'common.status.Rejected': { fr: 'Refusée', en: 'Rejected' },
  'common.status.Processed': { fr: 'Traitée', en: 'Processed' },
  'common.status.Completed': { fr: 'Finalisée', en: 'Completed' },
  'common.status.Archived': { fr: 'Archivée', en: 'Archived' },
  'common.status.To verify': { fr: 'À vérifier', en: 'To verify' },
  'common.status.Active': { fr: 'Actif', en: 'Active' },
  'common.status.Inactive': { fr: 'Inactif', en: 'Inactive' },
  'common.status.On leave': { fr: 'En congé', en: 'On leave' },
  'common.status.Terminated': { fr: 'Parti', en: 'Terminated' },

  // Leave types, as the API names them.
  'common.leaveType.Annual Leave': { fr: 'Congé payé', en: 'Annual Leave' },
  'common.leaveType.Sick Leave': { fr: 'Congé maladie', en: 'Sick Leave' },
  'common.leaveType.Unpaid Leave': { fr: 'Congé sans solde', en: 'Unpaid Leave' },
  'common.leaveType.Personal Day': { fr: 'Jour personnel', en: 'Personal Day' },
});
