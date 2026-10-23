import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import Button from '../ui/Button';
import { Field, FormAlert, Input } from '../ui/Field';
import type { MfaSetup } from '../../api';
import { useT } from '../../i18n';

interface MfaSetupFormProps {
  setup: MfaSetup;
  /** Resolves to the error to show, or null once the code is accepted. */
  onConfirm: (code: string) => Promise<string | null>;
}

// Light in both themes: scanners read dark modules on a light ground.
const QR_FRAME = 'self-center rounded-lg bg-white p-2'; // raw-color-ok: a QR code needs a light ground to scan

/** The secret as four-character groups, easier to type into an app by hand. */
function grouped(secret: string) {
  return secret.match(/.{1,4}/g)?.join(' ') ?? secret;
}

/**
 * Adding the account to an authenticator app (#44): scan the QR code, or type
 * the key, then prove it with the first code. The QR code is drawn by the
 * server as an SVG data URI, so no third party ever sees the secret.
 */
export default function MfaSetupForm({ setup, onConfirm }: MfaSetupFormProps) {
  const t = useT();
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const digits = code.replace(/\s/g, '');
    if (!/^\d{6}$/.test(digits)) {
      setError(t('auth.mfa.codeFormat'));
      return;
    }
    setChecking(true);
    const failure = await onConfirm(digits);
    setChecking(false);
    if (failure) setError(failure);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      {error && <FormAlert>{error}</FormAlert>}
      <ol className="flex flex-col gap-2 text-sm text-on-surface-variant list-decimal pl-5">
        <li>{t('auth.mfa.stepApp')}</li>
        <li>{t('auth.mfa.stepScan')}</li>
        <li>{t('auth.mfa.stepCode')}</li>
      </ol>
      <img
        src={setup.qrCode}
        alt={t('auth.mfa.qrAlt')}
        width={176}
        height={176}
        className={QR_FRAME}
      />
      <details className="text-sm">
        <summary className="cursor-pointer font-semibold text-secondary">{t('auth.mfa.cantScan')}</summary>
        <p className="mt-2 text-on-surface-variant">{t('auth.mfa.manualKey')}</p>
        <code className="mt-1 block break-all rounded-lg bg-surface-container-low p-2 font-mono select-all">
          {grouped(setup.secret)}
        </code>
      </details>
      <Field label={t('auth.mfa.code')}>
        {({ id, describedBy, invalid }) => (
          <Input
            id={id}
            aria-describedby={describedBy}
            invalid={invalid}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={7}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        )}
      </Field>
      <Button type="submit" className="self-start" loading={checking}>
        <ShieldCheck className="w-4 h-4" aria-hidden="true" />
        {t('auth.mfa.activate')}
      </Button>
    </form>
  );
}
