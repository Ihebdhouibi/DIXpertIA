import React, { useState, useEffect } from 'react';
import { Lock, CheckCircle, AlertCircle } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';

interface ResetPasswordProps {
  token: string;
  onComplete: () => void;
}

const MIN_LENGTH = 8;

export default function ResetPassword({ token, onComplete }: ResetPasswordProps) {
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
      const response = await fetch('/api/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, newPassword: password })
      });
      const data = await response.json();
      if (response.ok) {
        setSuccess(true);
        setTimeout(onComplete, 3000); // auto navigate to login after success
      } else {
        setError(data.detail || 'Something went wrong. Please try again.');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (validToken === false) {
    return (
      <AuthLayout title="Invalid reset link" subtitle="The reset token is missing or invalid.">
        <div className="flex items-center gap-3 text-error">
          <AlertCircle className="w-5 h-5 shrink-0" aria-hidden="true" />
          <p className="text-sm">Request a new link from the login screen.</p>
        </div>
        <Button size="lg" fullWidth onClick={onComplete}>
          Back to login
        </Button>
      </AuthLayout>
    );
  }

  if (success) {
    return (
      <AuthLayout title="Password updated">
        <div role="status" className="flex items-start gap-3 rounded-lg bg-success-container px-4 py-3 text-success">
          <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm">Your password has been reset. Redirecting you to login...</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Set a new password" subtitle="Choose a new password for your account.">
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
          {loading ? 'Updating...' : 'Reset password'}
        </Button>
      </form>
    </AuthLayout>
  );
}
