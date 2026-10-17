import { defineMessages } from '../define';

/** auth: sign-in, password reset, account activation. See ../define.ts; keys start with "auth.". */
export default defineMessages('auth', {
  'auth.invalidCredentials': {
    fr: 'Adresse e-mail ou mot de passe incorrect.',
    en: 'Incorrect email or password.',
  },
  'auth.networkError': {
    fr: 'Erreur réseau lors de la connexion. Veuillez réessayer.',
    en: 'Network error during sign-in. Please try again.',
  },

  'auth.networkRetry': { fr: 'Erreur réseau. Veuillez réessayer.', en: 'Network error. Please try again.' },
  'auth.somethingWrong': {
    fr: 'Une erreur est survenue. Veuillez réessayer.',
    en: 'Something went wrong. Please try again.',
  },
  'auth.email': { fr: 'Adresse e-mail', en: 'Email address' },
  'auth.emailPlaceholder': { fr: 'nom@dixpertia.com', en: 'name@dixpertia.com' },
  'auth.password': { fr: 'Mot de passe', en: 'Password' },
  'auth.backToLogin': { fr: 'Retour à la connexion', en: 'Back to login' },

  // Sign-in.
  'auth.login.title': { fr: 'Connexion', en: 'Welcome back' },
  'auth.login.subtitle': { fr: 'Connectez-vous à votre espace employé.', en: 'Sign in to your employee portal.' },
  'auth.login.backHome': { fr: "Retour à l'accueil", en: 'Back to Home' },
  'auth.login.fillAll': { fr: 'Veuillez remplir tous les champs.', en: 'Please fill in all fields.' },
  'auth.login.forgot': { fr: 'Mot de passe oublié ?', en: 'Forgot password?' },
  'auth.login.submit': { fr: 'Se connecter', en: 'Sign in' },

  // Forgotten password: asking for the link.
  'auth.forgot.title': { fr: 'Réinitialiser le mot de passe', en: 'Reset your password' },
  'auth.forgot.subtitle': {
    fr: 'Saisissez votre adresse e-mail, nous vous enverrons un lien de réinitialisation.',
    en: "Enter your email address and we'll send you a reset link.",
  },
  'auth.forgot.enterEmail': { fr: 'Veuillez saisir votre adresse e-mail.', en: 'Please enter your email address.' },
  'auth.forgot.sending': { fr: 'Envoi…', en: 'Sending...' },
  'auth.forgot.submit': { fr: 'Envoyer le lien', en: 'Send reset link' },
  'auth.forgot.checkEmail': { fr: 'Consultez vos e-mails', en: 'Check your email' },
  // The address sits between the two halves, in bold.
  'auth.forgot.sentBefore': { fr: 'Si un compte existe pour ', en: 'If an account exists for ' },
  'auth.forgot.sentAfter': {
    fr: ', un lien de réinitialisation vous a été envoyé.',
    en: ', a password reset link is on its way.',
  },

  // Setting a password from an e-mailed link: a reset, or a new account's activation (#62).
  'auth.reset.title': { fr: 'Nouveau mot de passe', en: 'Set a new password' },
  'auth.reset.subtitle': {
    fr: 'Choisissez un nouveau mot de passe pour votre compte.',
    en: 'Choose a new password for your account.',
  },
  'auth.reset.submit': { fr: 'Réinitialiser', en: 'Reset password' },
  'auth.reset.done': { fr: 'Mot de passe modifié', en: 'Password updated' },
  'auth.reset.doneMessage': {
    fr: 'Votre mot de passe a été réinitialisé et vos autres sessions fermées. Redirection vers la connexion…',
    en: 'Your password has been reset. You are signed out everywhere else. Redirecting you to login...',
  },
  'auth.reset.invalid': { fr: 'Lien de réinitialisation invalide', en: 'Invalid reset link' },
  'auth.activate.title': { fr: 'Activer votre compte', en: 'Activate your account' },
  'auth.activate.subtitle': {
    fr: 'Choisissez votre mot de passe de connexion.',
    en: 'Choose the password you will sign in with.',
  },
  'auth.activate.submit': { fr: 'Activer le compte', en: 'Activate account' },
  'auth.activate.done': { fr: 'Compte activé', en: 'Account activated' },
  'auth.activate.doneMessage': {
    fr: 'Votre compte est prêt. Redirection vers la connexion…',
    en: 'Your account is ready. Redirecting you to login...',
  },
  'auth.activate.invalid': { fr: "Lien d'activation invalide", en: 'Invalid activation link' },
  'auth.reset.missingToken': { fr: 'Jeton de réinitialisation manquant.', en: 'Missing reset token.' },
  'auth.reset.linkInvalid': { fr: 'Le lien est manquant ou invalide.', en: 'The link is missing or invalid.' },
  'auth.reset.askAdmin': {
    fr: "Demandez à votre administrateur un nouveau lien d'activation.",
    en: 'Ask your administrator to send a new activation link.',
  },
  'auth.reset.requestNew': {
    fr: "Demandez un nouveau lien depuis l'écran de connexion.",
    en: 'Request a new link from the login screen.',
  },
  'auth.reset.fillBoth': { fr: 'Veuillez remplir les deux champs.', en: 'Please fill in both fields.' },
  'auth.reset.tooShort': {
    fr: 'Le mot de passe doit comporter au moins {min} caractères.',
    en: 'Password must be at least {min} characters.',
  },
  'auth.reset.newPassword': { fr: 'Nouveau mot de passe', en: 'New password' },
  'auth.reset.minHint': { fr: 'Au moins {min} caractères.', en: 'At least {min} characters.' },
  'auth.reset.confirmPassword': { fr: 'Confirmer le mot de passe', en: 'Confirm password' },
  'auth.reset.mismatch': { fr: 'Les mots de passe ne correspondent pas.', en: 'Passwords do not match.' },
  'auth.reset.saving': { fr: 'Enregistrement…', en: 'Saving...' },
});
