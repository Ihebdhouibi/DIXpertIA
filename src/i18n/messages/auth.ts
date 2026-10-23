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

  // Two-factor authentication (#44): the sign-in's second step, and Settings.
  'auth.mfa.challengeTitle': { fr: 'Vérification en deux étapes', en: 'Two-step verification' },
  'auth.mfa.challengeSubtitle': {
    fr: "Saisissez le code à 6 chiffres affiché par votre application d'authentification.",
    en: 'Enter the 6-digit code shown in your authenticator app.',
  },
  'auth.mfa.enrolTitle': { fr: "Activez l'authentification à deux facteurs", en: 'Set up two-factor authentication' },
  'auth.mfa.enrolSubtitle': {
    fr: 'Votre rôle exige un second facteur. Configurez-le une fois pour accéder à votre espace.',
    en: 'Your role requires a second factor. Set it up once to reach your portal.',
  },
  'auth.mfa.preparing': { fr: 'Préparation…', en: 'Preparing...' },
  'auth.mfa.code': { fr: 'Code à 6 chiffres', en: '6-digit code' },
  'auth.mfa.codeFormat': { fr: 'Saisissez les 6 chiffres du code.', en: 'Enter the 6 digits of the code.' },
  'auth.mfa.recoveryCode': { fr: 'Code de secours', en: 'Recovery code' },
  'auth.mfa.recoveryEmpty': { fr: 'Saisissez un de vos codes de secours.', en: 'Enter one of your recovery codes.' },
  'auth.mfa.useRecovery': { fr: 'Téléphone perdu ? Utiliser un code de secours', en: 'Lost your phone? Use a recovery code' },
  'auth.mfa.useApp': { fr: "Utiliser le code de l'application", en: 'Use the code from the app' },
  'auth.mfa.verify': { fr: 'Vérifier', en: 'Verify' },
  'auth.mfa.stepApp': {
    fr: "Installez une application d'authentification (Google Authenticator, Microsoft Authenticator, Aegis…).",
    en: 'Install an authenticator app (Google Authenticator, Microsoft Authenticator, Aegis...).',
  },
  'auth.mfa.stepScan': { fr: "Scannez ce QR code avec l'application.", en: 'Scan this QR code with the app.' },
  'auth.mfa.stepCode': { fr: "Saisissez le code qu'elle affiche.", en: 'Enter the code it shows.' },
  'auth.mfa.qrAlt': {
    fr: "QR code à scanner avec votre application d'authentification",
    en: 'QR code to scan with your authenticator app',
  },
  'auth.mfa.cantScan': { fr: 'Impossible de scanner ?', en: "Can't scan it?" },
  'auth.mfa.manualKey': { fr: "Saisissez cette clé dans l'application :", en: 'Enter this key in the app:' },
  'auth.mfa.activate': { fr: 'Activer', en: 'Turn on' },
  'auth.mfa.codesTitle': { fr: 'Codes de secours', en: 'Recovery codes' },
  'auth.mfa.codesIntro': {
    fr: 'Conservez ces codes en lieu sûr (un gestionnaire de mots de passe, par exemple). Chacun permet une connexion si vous perdez votre téléphone, une seule fois. Ils ne seront plus affichés.',
    en: 'Keep these codes somewhere safe, such as a password manager. Each signs you in once if you lose your phone. They will not be shown again.',
  },
  'auth.mfa.copy': { fr: 'Copier', en: 'Copy' },
  'auth.mfa.copied': { fr: 'Copiés', en: 'Copied' },
  'auth.mfa.download': { fr: 'Télécharger', en: 'Download' },
  'auth.mfa.codesKept': { fr: "J'ai conservé mes codes de secours.", en: 'I have kept my recovery codes.' },
  'auth.mfa.continue': { fr: 'Continuer', en: 'Continue' },
  'auth.mfa.done': { fr: 'Terminé', en: 'Done' },
  'auth.mfa.settingsTitle': { fr: 'Authentification à deux facteurs', en: 'Two-factor authentication' },
  'auth.mfa.statusOn': {
    fr: 'Activée. Codes de secours restants : {left}.',
    en: 'On. Recovery codes left: {left}.',
  },
  'auth.mfa.statusOff': {
    fr: 'Désactivée. Ajoutez un code de votre téléphone à la connexion, en plus du mot de passe.',
    en: 'Off. Add a code from your phone to the sign-in, on top of the password.',
  },
  'auth.mfa.statusRequired': {
    fr: 'Exigée pour votre rôle. Activez-la maintenant.',
    en: 'Required for your role. Turn it on now.',
  },
  'auth.mfa.enable': { fr: 'Activer', en: 'Turn on' },
  'auth.mfa.enabled': {
    fr: 'Authentification à deux facteurs activée. Vos autres sessions ont été fermées.',
    en: 'Two-factor authentication is on. You are signed out everywhere else.',
  },
  'auth.mfa.renew': { fr: 'Nouveaux codes de secours', en: 'New recovery codes' },
  'auth.mfa.renewIntro': {
    fr: "Les anciens codes cesseront de fonctionner. Saisissez un code de l'application pour confirmer.",
    en: 'The old codes will stop working. Enter a code from the app to confirm.',
  },
  'auth.mfa.disable': { fr: 'Désactiver', en: 'Turn off' },
  'auth.mfa.disableIntro': {
    fr: 'Votre compte ne sera plus protégé que par le mot de passe. Saisissez-le pour confirmer.',
    en: 'Your account will be protected by the password alone. Enter it to confirm.',
  },
  'auth.mfa.passwordEmpty': { fr: 'Saisissez votre mot de passe.', en: 'Enter your password.' },
  'auth.mfa.disabled': {
    fr: 'Authentification à deux facteurs désactivée. Vos autres sessions ont été fermées.',
    en: 'Two-factor authentication is off. You are signed out everywhere else.',
  },
  'auth.mfa.cancel': { fr: 'Annuler', en: 'Cancel' },

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
