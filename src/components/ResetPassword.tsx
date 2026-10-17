import React, { useState, useEffect } from 'react';
import { Lock, CheckCircle, AlertCircle } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';

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

const TEXT = {
  reset: {
    endpoint: '/api/reset-password',
    title: 'Set a new password',
    subtitle: 'Choose a new password for your account.',
    submit: 'Reset password',
    done: 'Password updated',
    doneMessage: 'Your password has been reset. You are signed out everywhere else. Redirecting you to login...',
    invalid: 'Invalid reset link',
  },
  activate: {
    endpoint: '/api/activate',
    title: 'Activate your account',
    subtitle: 'Choose the password you will sign in with.',
    submit: 'Activate account',
    done: 'Account activated',
    doneMessage: 'Your account is ready. Redirecting you to login...',
    invalid: 'Invalid activation link',
  },
};

export default function ResetPassword({ token, mode = 'reset', onComplete }: ResetPasswordProps) {
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
      setError('Missing reset token.');
    } else {
      setValidToken(true);
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMismatch(false);
    if (!password || !confirmPassword) {
      setError('Please fill in both fields.');
      return;
    }
    if (password.length < MIN_LENGTH) {
      setError(`Password must be at least ${MIN_LENGTH} characters.`);
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
        setError(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (validToken === false) {
    return (
      <AuthLayout title={text.invalid} subtitle="The link is missing or invalid.">
        <div className="flex items-center gap-3 text-error">
          <AlertCircle className="w-5 h-5 shrink-0" aria-hidden="true" />
          <p className="text-sm">
            {mode === 'activate'
              ? 'Ask your administrator to send a new activation link.'
              : 'Request a new link from the login screen.'}
          </p>
        </div>
        <Button size="lg" fullWidth onClick={onComplete}>
          Back to login
        </Button>
      </AuthLayout>
    );
  }

  if (success) {
    return (
      <AuthLayout title={text.done}>
        <div role="status" className="flex items-start gap-3 rounded-lg bg-success-container px-4 py-3 text-success">
          <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm">{text.doneMessage}</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title={text.title} subtitle={text.subtitle}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label="New password" hint={`At least ${MIN_LENGTH} characters.`}>
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
        <Field label="Confirm password" error={mismatch ? 'Passwords do not match.' : undefined}>
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
          {loading ? 'Saving...' : text.submit}
        </Button>
      </form>
    </AuthLayout>
  );
}
