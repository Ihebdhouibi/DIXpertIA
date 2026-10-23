import React, { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, RefreshCw, ShieldOff } from 'lucide-react';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';
import { useToast } from './ui/feedback';
import MfaSetupForm from './mfa/MfaSetupForm';
import RecoveryCodes from './mfa/RecoveryCodes';
import * as api from '../api';
import { useT } from '../i18n';

type Mode =
  | { kind: 'idle' }
  | { kind: 'setup'; setup: api.MfaSetup }
  | { kind: 'codes'; codes: string[] }
  | { kind: 'renew' }
  | { kind: 'disable' };

function message(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Two-factor authentication on one's own account (#44). Hidden while the
 * server has no MFA_ENCRYPTION_KEY, since nothing here could work then.
 */
export default function TwoFactorSettings() {
  const t = useT();
  const toast = useToast();
  const [status, setStatus] = useState<api.MfaStatus | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: 'idle' });
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.mfa.status().then(setStatus).catch(() => setStatus(null));
  }, []);
  useEffect(load, [load]);

  const go = (next: Mode) => {
    setMode(next);
    setValue('');
    setError('');
  };

  const start = async () => {
    setBusy(true);
    setError('');
    try {
      go({ kind: 'setup', setup: await api.mfa.setup() });
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (code: string) => {
    try {
      const result = await api.mfa.confirm(code);
      go({ kind: 'codes', codes: result.recoveryCodes });
      toast(t('auth.mfa.enabled'));
      return null;
    } catch (e) {
      return message(e);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!value.trim()) {
      setError(mode.kind === 'disable' ? t('auth.mfa.passwordEmpty') : t('auth.mfa.codeFormat'));
      return;
    }
    setBusy(true);
    try {
      if (mode.kind === 'renew') {
        const result = await api.mfa.renewRecoveryCodes(value.replace(/\s/g, ''));
        go({ kind: 'codes', codes: result.recoveryCodes });
      } else {
        await api.mfa.disable(value);
        go({ kind: 'idle' });
        toast(t('auth.mfa.disabled'));
        load();
      }
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  };

  if (!status?.available) return null;

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6">
      <h2 className="text-body-lg font-bold text-on-surface mb-1 flex items-center gap-2">
        <ShieldCheck className="w-5 h-5 text-primary" />
        {t('auth.mfa.settingsTitle')}
      </h2>
      <p className="text-sm text-on-surface-variant mb-4">
        {status.enabled
          ? t('auth.mfa.statusOn', { left: status.recoveryCodesLeft })
          : status.required ? t('auth.mfa.statusRequired') : t('auth.mfa.statusOff')}
      </p>

      <div className="md:max-w-md">
        {mode.kind === 'setup' && <MfaSetupForm setup={mode.setup} onConfirm={confirm} />}

        {mode.kind === 'codes' && (
          <RecoveryCodes codes={mode.codes} doneLabel={t('auth.mfa.done')} onDone={() => { go({ kind: 'idle' }); load(); }} />
        )}

        {(mode.kind === 'renew' || mode.kind === 'disable') && (
          <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
            {error && <FormAlert>{error}</FormAlert>}
            <p className="text-sm text-on-surface-variant">
              {mode.kind === 'renew' ? t('auth.mfa.renewIntro') : t('auth.mfa.disableIntro')}
            </p>
            <Field label={mode.kind === 'renew' ? t('auth.mfa.code') : t('common.settings.currentPassword')}>
              {({ id }) => (
                <Input
                  id={id}
                  type={mode.kind === 'disable' ? 'password' : 'text'}
                  inputMode={mode.kind === 'renew' ? 'numeric' : undefined}
                  autoComplete={mode.kind === 'renew' ? 'one-time-code' : 'current-password'}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                />
              )}
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant={mode.kind === 'disable' ? 'danger' : 'primary'} loading={busy}>
                {mode.kind === 'renew' ? t('auth.mfa.renew') : t('auth.mfa.disable')}
              </Button>
              <Button type="button" variant="secondary" onClick={() => go({ kind: 'idle' })} disabled={busy}>
                {t('auth.mfa.cancel')}
              </Button>
            </div>
          </form>
        )}

        {mode.kind === 'idle' && (
          <div className="flex flex-col gap-3">
            {error && <FormAlert>{error}</FormAlert>}
            <div className="flex flex-wrap gap-2">
              {!status.enabled && (
                <Button onClick={start} loading={busy}>
                  <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                  {t('auth.mfa.enable')}
                </Button>
              )}
              {status.enabled && (
                <Button variant="secondary" onClick={() => go({ kind: 'renew' })}>
                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                  {t('auth.mfa.renew')}
                </Button>
              )}
              {/* A role that requires it cannot turn it off; the server refuses as well. */}
              {status.enabled && !status.required && (
                <Button variant="danger" onClick={() => go({ kind: 'disable' })}>
                  <ShieldOff className="w-4 h-4" aria-hidden="true" />
                  {t('auth.mfa.disable')}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
