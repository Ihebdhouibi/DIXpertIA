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
});
