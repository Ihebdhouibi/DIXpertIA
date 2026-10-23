import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, KeyRound } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';
import LanguageToggle from './LanguageToggle';
import MfaSetupForm from './mfa/MfaSetupForm';
import RecoveryCodes from './mfa/RecoveryCodes';
import * as api from '../api';
import type { User } from '../types';
import { useT } from '../i18n';

/** What the password step leads to when the account has, or needs, a second factor (#44). */
export type MfaStep = { kind: 'challenge'; token: string } | { kind: 'enrol'; token: string };

export interface Session {
  access_token: string;
  user: User;
}

interface MfaSignInProps {
  step: MfaStep;
  onSignedIn: (session: Session) => Promise<void>;
  /** Back to the password: the step's token lasts minutes, then a new sign-in is needed. */
  onRestart: () => void;
}

function message(error: unknown, fallback: string) {
  return error instanceof api.ApiError ? error.message : fallback;
}

function session(result: { access_token?: string | null; user?: User | null }): Session | null {
  return result.access_token && result.user ? { access_token: result.access_token, user: result.user } : null;
}

/** The code from the authenticator app, or one of the recovery codes for a lost phone. */
function Challenge({ token, onSignedIn }: { token: string; onSignedIn: MfaSignInProps['onSignedIn'] }) {
  const t = useT();
  const [useRecovery, setUseRecovery] = useState(false);
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const answer = value.trim();
    if (!useRecovery && !/^\d{6}$/.test(answer.replace(/\s/g, ''))) {
      setError(t('auth.mfa.codeFormat'));
      return;
    }
    if (useRecovery && !answer) {
      setError(t('auth.mfa.recoveryEmpty'));
      return;
    }
    setChecking(true);
    try {
      const result = await api.mfa.verify(
        token,
        useRecovery ? { recoveryCode: answer.toLowerCase() } : { code: answer.replace(/\s/g, '') },
      );
      const signedIn = session(result);
      if (!signedIn) throw new Error(t('auth.somethingWrong'));
      await onSignedIn(signedIn);
    } catch (error) {
      setError(message(error, t('auth.networkRetry')));
      setChecking(false);
    }
  };

  const switchMode = () => {
    setUseRecovery(!useRecovery);
    setValue('');
    setError('');
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      {error && <FormAlert>{error}</FormAlert>}
      <Field label={useRecovery ? t('auth.mfa.recoveryCode') : t('auth.mfa.code')}>
        {({ id, describedBy, invalid }) => (
          <Input
            id={id}
            aria-describedby={describedBy}
            invalid={invalid}
            icon={KeyRound}
            inputMode={useRecovery ? 'text' : 'numeric'}
            autoComplete={useRecovery ? 'off' : 'one-time-code'}
            autoFocus
            maxLength={useRecovery ? 20 : 7}
            placeholder={useRecovery ? 'xxxxx-xxxxx' : undefined}
            required
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        )}
      </Field>
      <button
        type="button"
        onClick={switchMode}
        className="self-start text-xs font-semibold text-secondary hover:underline cursor-pointer rounded"
      >
        {useRecovery ? t('auth.mfa.useApp') : t('auth.mfa.useRecovery')}
      </button>
      <Button type="submit" size="lg" fullWidth loading={checking}>
        {t('auth.mfa.verify')}
        <ArrowRight className="w-4 h-4" aria-hidden="true" />
      </Button>
    </form>
  );
}

/** A role that requires a second factor, signing in without one yet: set it up first. */
function Enrolment({ token, onSignedIn }: { token: string; onSignedIn: MfaSignInProps['onSignedIn'] }) {
  const t = useT();
  const [setup, setSetup] = useState<api.MfaSetup | null>(null);
  const [error, setError] = useState('');
  const [done, setDone] = useState<{ codes: string[]; session: Session } | null>(null);
  // Each set-up call draws a new secret; StrictMode's second effect would leave
  // the QR code on screen out of step with the one the server kept.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    api.mfa.enrolSetup(token)
      .then(setSetup)
      .catch((error) => setError(message(error, t('auth.networkRetry'))));
  }, [token, t]);

  const confirm = async (code: string) => {
    try {
      const result = await api.mfa.enrolConfirm(token, code);
      const signedIn = session(result);
      if (!signedIn) return t('auth.somethingWrong');
      setDone({ codes: result.recoveryCodes, session: signedIn });
      return null;
    } catch (error) {
      return message(error, t('auth.networkRetry'));
    }
  };

  if (done) {
    return (
      <RecoveryCodes codes={done.codes} doneLabel={t('auth.mfa.continue')} onDone={() => onSignedIn(done.session)} />
    );
  }
  if (error) return <FormAlert>{error}</FormAlert>;
  if (!setup) return <p className="text-sm text-on-surface-variant" role="status">{t('auth.mfa.preparing')}</p>;
  return <MfaSetupForm setup={setup} onConfirm={confirm} />;
}

export default function MfaSignIn({ step, onSignedIn, onRestart }: MfaSignInProps) {
  const t = useT();
  const enrol = step.kind === 'enrol';
  return (
    <AuthLayout
      title={enrol ? t('auth.mfa.enrolTitle') : t('auth.mfa.challengeTitle')}
      subtitle={enrol ? t('auth.mfa.enrolSubtitle') : t('auth.mfa.challengeSubtitle')}
      aside={<LanguageToggle />}
      footer={
        <Button variant="ghost" size="sm" onClick={onRestart} className="-ml-3">
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          {t('auth.backToLogin')}
        </Button>
      }
    >
      {enrol
        ? <Enrolment token={step.token} onSignedIn={onSignedIn} />
        : <Challenge token={step.token} onSignedIn={onSignedIn} />}
    </AuthLayout>
  );
}
