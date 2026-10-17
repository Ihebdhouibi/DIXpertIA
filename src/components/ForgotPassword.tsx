import React, { useState } from 'react';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';
import LanguageToggle from './LanguageToggle';
import { useT } from '../i18n';

interface ForgotPasswordProps {
  onBack: () => void;
}

export default function ForgotPassword({ onBack }: ForgotPasswordProps) {
  const t = useT();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email) {
      setError(t('auth.forgot.enterEmail'));
      return;
    }
    setLoading(true);
    try {
      const response = await fetch('/api/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await response.json();
      if (response.ok) {
        setSent(true);
      } else {
        setError(data.detail || t('auth.somethingWrong'));
      }
    } catch (err) {
      setError(t('auth.networkRetry'));
    } finally {
      setLoading(false);
    }
  };

  const backToLogin = (
    <Button variant="ghost" size="sm" onClick={onBack} className="-ml-3">
      <ArrowLeft className="w-4 h-4" aria-hidden="true" />
      {t('auth.backToLogin')}
    </Button>
  );

  if (sent) {
    return (
      <AuthLayout title={t('auth.forgot.checkEmail')} footer={backToLogin} aside={<LanguageToggle />}>
        <div role="status" className="flex items-start gap-3 rounded-lg bg-success-container px-4 py-3 text-success">
          <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm">
            {t('auth.forgot.sentBefore')}
            <span className="font-semibold break-all">{email}</span>
            {t('auth.forgot.sentAfter')}
          </p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={t('auth.forgot.title')}
      subtitle={t('auth.forgot.subtitle')}
      aside={<LanguageToggle />}
      footer={backToLogin}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label={t('auth.email')}>
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              invalid={invalid}
              icon={Mail}
              type="email"
              autoComplete="email"
              placeholder={t('auth.emailPlaceholder')}
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          )}
        </Field>
        <Button type="submit" size="lg" fullWidth loading={loading} className="mt-2">
          {loading ? t('auth.forgot.sending') : t('auth.forgot.submit')}
        </Button>
      </form>
    </AuthLayout>
  );
}
