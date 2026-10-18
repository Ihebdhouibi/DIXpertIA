import React, { useState, useEffect } from 'react';
import { Lock, CheckCircle, AlertCircle } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';
import LanguageToggle from './LanguageToggle';
import { useT, type MessageKey } from '../i18n';

interface ResetPasswordProps {
  token: string;
  /**
   * 'reset' for a forgotten password, 'activate' for a new account's first
   * password (#62). Same form; each link only works on its own endpoint.
   */
  mode?: 'reset' | 'activate';
  onComplete: () => void;
}

// Mirrors MIN_PASSWORD_LENGTH in app/core/security.py, which is what decides.
const MIN_LENGTH = 12;

// Texts are message keys, translated at render (#135).
type ModeText = { endpoint: string } & Record<'title' | 'subtitle' | 'submit' | 'done' | 'doneMessage' | 'invalid', MessageKey>;

const TEXT: Record<'reset' | 'activate', ModeText> = {
  reset: {
    endpoint: '/api/reset-password',
    title: 'auth.reset.title',
    subtitle: 'auth.reset.subtitle',
    submit: 'auth.reset.submit',
    done: 'auth.reset.done',
    doneMessage: 'auth.reset.doneMessage',
    invalid: 'auth.reset.invalid',
  },
  activate: {
    endpoint: '/api/activate',
    title: 'auth.activate.title',
    subtitle: 'auth.activate.subtitle',
    submit: 'auth.activate.submit',
    done: 'auth.activate.done',
    doneMessage: 'auth.activate.doneMessage',
    invalid: 'auth.activate.invalid',
  },
};

export default function ResetPassword({ token, mode = 'reset', onComplete }: ResetPasswordProps) {
  const t = useT();
  const text = TEXT[mode];
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [mismatch, setMismatch] = useState(false);
  const [validToken, setValidToken] = useState<boolean | null>(null);

  // Check token validity on mount (optional – we can just rely on the reset call)
  useEffect(() => {
    if (!token) {
      setValidToken(false);
      setError(t('auth.reset.missingToken'));
    } else {
      setValidToken(true);
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMismatch(false);
    if (!password || !confirmPassword) {
      setError(t('auth.reset.fillBoth'));
      return;
    }
    if (password.length < MIN_LENGTH) {
      setError(t('auth.reset.tooShort', { min: MIN_LENGTH }));
      return;
    }
    if (password !== confirmPassword) {
      setMismatch(true);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(text.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, newPassword: password })
      });
      const data = await response.json();
      if (response.ok) {
        setSuccess(true);
        setTimeout(onComplete, 3000); // auto navigate to login after success
      } else {
        // A refused password comes back as a string; a malformed request as a
        // list of field errors, which would render as "[object Object]".
        setError(typeof data.detail === 'string' ? data.detail : t('auth.somethingWrong'));
      }
    } catch (err) {
      setError(t('auth.networkRetry'));
    } finally {
      setLoading(false);
    }
  };

  if (validToken === false) {
    return (
      <AuthLayout title={t(text.invalid)} subtitle={t('auth.reset.linkInvalid')} aside={<LanguageToggle />}>
        <div className="flex items-center gap-3 text-error">
          <AlertCircle className="w-5 h-5 shrink-0" aria-hidden="true" />
          <p className="text-sm">
            {mode === 'activate'
              ? t('auth.reset.askAdmin')
              : t('auth.reset.requestNew')}
          </p>
        </div>
        <Button size="lg" fullWidth onClick={onComplete}>
          {t('auth.backToLogin')}
        </Button>
      </AuthLayout>
    );
  }

  if (success) {
    return (
      <AuthLayout title={t(text.done)} aside={<LanguageToggle />}>
        <div role="status" className="flex items-start gap-3 rounded-lg bg-success-container px-4 py-3 text-success">
          <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm">{t(text.doneMessage)}</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title={t(text.title)} subtitle={t(text.subtitle)} aside={<LanguageToggle />}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label={t('auth.reset.newPassword')} hint={t('auth.reset.minHint', { min: MIN_LENGTH })}>
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              invalid={invalid}
              icon={Lock}
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('auth.reset.confirmPassword')} error={mismatch ? t('auth.reset.mismatch') : undefined}>
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              invalid={invalid}
              icon={Lock}
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          )}
        </Field>
        <Button type="submit" size="lg" fullWidth loading={loading} className="mt-2">
          {loading ? t('auth.reset.saving') : t(text.submit)}
        </Button>
      </form>
    </AuthLayout>
  );
}
