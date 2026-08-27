import React, { useState, useEffect } from 'react';
import { Lock, CheckCircle, AlertCircle } from 'lucide-react';
import { motion } from 'motion/react';

interface ResetPasswordProps {
  token: string;
  onComplete: () => void;
}

export default function ResetPassword({ token, onComplete }: ResetPasswordProps) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
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
    if (!password || !confirmPassword) {
      setError('Please fill in both fields.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
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
      <div className="min-h-screen w-full flex items-center justify-center p-4 bg-[#e0f2fe]">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
          <AlertCircle className="w-12 h-12 text-error mx-auto mb-4" />
          <h2 className="text-h2 font-semibold text-on-surface">Invalid Reset Link</h2>
          <p className="text-body-sm text-on-surface-variant mt-2">The reset token is missing or invalid.</p>
          <button onClick={onComplete} className="mt-4 bg-primary text-white px-4 py-2 rounded-lg font-semibold">
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-[#e0f2fe] relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-10">
        <div className="absolute -top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full bg-primary-container/20 blur-3xl"></div>
        <div className="absolute -bottom-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-secondary-fixed/30 blur-3xl"></div>
      </div>

      <main className="w-full max-w-[480px] relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden"
        >
          <div className="h-2 w-full bg-primary"></div>
          <div className="p-8 flex flex-col gap-6">
            {!success ? (
              <>
                <div className="text-center">
                  <div className="font-sans text-h2 font-black text-primary tracking-tight mb-2">Set New Password</div>
                  <p className="text-body-sm text-on-surface-variant mt-2">Choose a new password for your account.</p>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs font-semibold text-red-800 text-center">
                      {error}
                    </div>
                  )}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-on-surface-variant" htmlFor="password">New Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                      <input
                        className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition text-body-sm"
                        id="password"
                        placeholder="••••••••"
                        required
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                      />
                    </div>
                    <p className="text-xs text-outline">At least 8 characters.</p>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-on-surface-variant" htmlFor="confirmPassword">Confirm Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                      <input
                        className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition text-body-sm"
                        id="confirmPassword"
                        placeholder="••••••••"
                        required
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="mt-2 w-full bg-primary hover:bg-primary/95 text-white font-semibold py-3 rounded-lg transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {loading ? 'Updating...' : 'Reset Password'}
                  </button>
                </form>
              </>
            ) : (
              <div className="text-center space-y-4 py-4">
                <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-secondary-fixed/30 text-secondary mb-4">
                  <CheckCircle className="w-10 h-10 text-[#137333]" />
                </div>
                <h2 className="text-h2 font-semibold text-primary">Password Updated</h2>
                <p className="text-body-sm text-on-surface-variant">Your password has been reset successfully.</p>
                <p className="text-caption text-on-surface-variant">You will be redirected to login shortly...</p>
              </div>
            )}
          </div>
        </motion.div>
      </main>
    </div>
  );
}