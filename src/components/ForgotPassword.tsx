import React, { useState } from 'react';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import { motion } from 'motion/react';

interface ForgotPasswordProps {
  onBack: () => void;
}

export default function ForgotPassword({ onBack }: ForgotPasswordProps) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email) {
      setError('Please enter your email address.');
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
        setError(data.detail || 'Something went wrong. Please try again.');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
            {!sent ? (
              <>
                <div className="text-center">
                  <div className="font-sans text-h2 font-black text-primary tracking-tight mb-2">Reset Password</div>
                  <p className="text-body-sm text-on-surface-variant mt-2">
                    Enter your email address and we'll send you a reset link.
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs font-semibold text-red-800 text-center">
                      {error}
                    </div>
                  )}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-on-surface-variant" htmlFor="email">Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                      <input
                        className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition text-body-sm"
                        id="email"
                        placeholder="name@dixpertia.com"
                        required
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="mt-2 w-full bg-primary hover:bg-primary/95 text-white font-semibold py-3 rounded-lg transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {loading ? 'Sending...' : 'Send Reset Link'}
                  </button>
                </form>

                <div className="text-center mt-2 pt-4 border-t border-outline-variant/30">
                  <button
                    onClick={onBack}
                    className="inline-flex items-center text-body-sm font-semibold text-secondary hover:text-primary transition cursor-pointer"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Login
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center space-y-4 py-4">
                <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-secondary-fixed/30 text-secondary mb-4">
                  <CheckCircle className="w-10 h-10 text-[#137333]" />
                </div>
                <h2 className="text-h2 font-semibold text-primary">Check your email</h2>
                <p className="text-body-sm text-on-surface-variant">
                  We've sent a password reset link to <br />
                  <span className="font-bold text-on-surface break-all">{email}</span>
                </p>
                <button
                  onClick={onBack}
                  className="mt-4 text-secondary hover:text-primary font-semibold text-body-sm underline transition"
                >
                  Back to Login
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </main>
    </div>
  );
}