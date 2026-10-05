import React, { useState } from 'react';
import { Mail, Lock, ArrowRight, ArrowLeft } from 'lucide-react';
import AuthLayout from './ui/AuthLayout';
import Button from './ui/Button';
import { Field, FormAlert, Input } from './ui/Field';

interface LoginProps {
  onLogin: (email: string, password: string) => void;
  onBackHome?: () => void;
  onForgotPassword: () => void;
}

// The forgot-password flow lives in ForgotPassword.tsx. This component used to
// carry a second, unreachable copy of it (App always passes onForgotPassword).
export default function Login({ onLogin, onBackHome, onForgotPassword }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    // Do not guess the role here. It previously inferred 'admin' from the email
    // containing "admin"; the value was discarded server-side, but the pattern
    // was a genuine privilege escalation in the now-deleted Registration.tsx.
    // The role comes from the /api/login response.
    onLogin(email, password);
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your employee portal."
      footer={
        onBackHome && (
          <Button variant="ghost" size="sm" onClick={onBackHome} className="-ml-3">
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back to Home
          </Button>
        )
      }
    >
      <form onSubmit={handleLogin} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label="Email address">
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              invalid={invalid}
              icon={Mail}
              type="email"
              autoComplete="username"
              placeholder="name@dixpertia.com"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          )}
        </Field>
        <Field
          label="Password"
          labelAside={
            <button
              type="button"
              onClick={onForgotPassword}
              className="text-xs font-semibold text-secondary hover:underline cursor-pointer rounded"
            >
              Forgot password?
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
        <Button type="submit" size="lg" fullWidth className="mt-2">
          Sign in
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </Button>
      </form>
    </AuthLayout>
  );
}
