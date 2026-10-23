import React, { useState } from 'react';
import { Mail, Lock, ArrowRight, ArrowLeft } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';
import LanguageToggle from './LanguageToggle';
import MfaSignIn, { type MfaStep, type Session } from './MfaSignIn';
import { useT } from '../i18n';

interface LoginProps {
  /**
   * Resolves to the error to show, to the second step when the account has or
   * needs two-factor authentication (#44), or to null once signed in.
   */
  onLogin: (email: string, password: string) => Promise<string | MfaStep | null>;
  /** Ends the second step: the session it earned. */
  onSession: (session: Session) => Promise<void>;
  onBackHome?: () => void;
  onForgotPassword: () => void;
}

// The forgot-password flow lives in ForgotPassword.tsx. This component used to
// carry a second, unreachable copy of it (App always passes onForgotPassword).
export default function Login({ onLogin, onSession, onBackHome, onForgotPassword }: LoginProps) {
  const t = useT();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const [signingIn, setSigningIn] = useState(false);
  const [mfaStep, setMfaStep] = useState<MfaStep | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError(t('auth.login.fillAll'));
      return;
    }
    // Do not guess the role here. It previously inferred 'admin' from the email
    // containing "admin"; the value was discarded server-side, but the pattern
    // was a genuine privilege escalation in the now-deleted Registration.tsx.
    // The role comes from the /api/login response.
    setSigningIn(true);
    const outcome = await onLogin(email, password);
    setSigningIn(false);
    if (typeof outcome === 'string') setError(outcome);
    else if (outcome) {
      // The password has done its job; it is not kept for the second step.
      setPassword('');
      setMfaStep(outcome);
    }
  };

  if (mfaStep) {
    return <MfaSignIn step={mfaStep} onSignedIn={onSession} onRestart={() => setMfaStep(null)} />;
  }

  return (
    <AuthLayout
      title={t('auth.login.title')}
      subtitle={t('auth.login.subtitle')}
      aside={<LanguageToggle />}
      footer={
        onBackHome && (
          <Button variant="ghost" size="sm" onClick={onBackHome} className="-ml-3">
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            {t('auth.login.backHome')}
          </Button>
        )
      }
    >
      <form onSubmit={handleLogin} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label={t('auth.email')}>
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              invalid={invalid}
              icon={Mail}
              type="email"
              autoComplete="username"
              placeholder={t('auth.emailPlaceholder')}
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          )}
        </Field>
        <Field
          label={t('auth.password')}
          labelAside={
            <button
              type="button"
              onClick={onForgotPassword}
              className="text-xs font-semibold text-secondary hover:underline cursor-pointer rounded"
            >
              {t('auth.login.forgot')}
            </button>
          }
        >
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              invalid={invalid}
              icon={Lock}
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
        </Field>
        <Button type="submit" size="lg" fullWidth className="mt-2" loading={signingIn}>
          {t('auth.login.submit')}
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </Button>
      </form>
    </AuthLayout>
  );
}
