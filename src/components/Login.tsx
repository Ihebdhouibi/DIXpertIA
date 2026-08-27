import React, { useState } from 'react';
import { Mail, Lock, ArrowRight, ArrowLeft, CheckCircle, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';
import { UserRole } from '../types';

interface LoginProps {
  onLogin: (role: UserRole, email: string, firstName: string, lastName: string, password: string) => void;
  onBackHome?: () => void;
  onForgotPassword?: () => void;  // NEW
}

export default function Login({ onLogin, onBackHome, onForgotPassword }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetSent, setResetSent] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    const role: UserRole = email.toLowerCase().includes('admin') ? 'admin' : 'employee';
    const firstName = email.split('@')[0] || 'User';
    const lastName = '';
    onLogin(role, email, firstName, lastName, password);
  };

  const handleForgotPassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail) return;
    setResetSent(true);
  };

  const handleResend = () => {
    setIsResending(true);
    setTimeout(() => setIsResending(false), 1200);
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-[#e0f2fe] relative overflow-hidden bg-pattern">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-10">
        <div className="absolute -top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full bg-primary-container/20 blur-3xl"></div>
        <div className="absolute -bottom-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-secondary-fixed/30 blur-3xl"></div>
      </div>

      <main className="w-full max-w-[480px] relative z-10">
        {!showForgot ? (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden"
          >
            <div className="h-2 w-full bg-primary"></div>
            <div className="p-8 flex flex-col gap-6">
              <div className="text-center">
                <div className="font-sans text-h2 font-black text-primary tracking-tight mb-2">DIXpertIA</div>
                <h1 className="font-sans text-h1 text-on-surface font-semibold">Welcome Back</h1>
                <p className="text-body-sm text-on-surface-variant mt-2">Sign in to your employee portal.</p>
              </div>

              <form onSubmit={handleLogin} className="flex flex-col gap-4">
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs font-semibold text-red-800 text-center">
                    {error}
                  </div>
                )}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-on-surface-variant" htmlFor="loginEmail">Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                    <input
                      className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition text-body-sm"
                      id="loginEmail"
                      placeholder="name@dixpertia.com"
                      required
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-medium text-on-surface-variant" htmlFor="loginPassword">Password</label>
                    <button
                      type="button"
                      onClick={() => {
                        if (onForgotPassword) onForgotPassword();
                        else setShowForgot(true);
                      }}
                      className="text-xs text-secondary hover:underline cursor-pointer"
                    >
                      Forgot?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                    <input
                      className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition text-body-sm"
                      id="loginPassword"
                      placeholder="••••••••"
                      required
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                </div>

                <button
                  className="mt-4 w-full bg-primary hover:bg-primary/95 text-white font-semibold py-3 rounded-lg transition flex items-center justify-center gap-2 shadow-sm"
                  type="submit"
                >
                  Sign In
                  <ArrowRight className="w-5 h-5" />
                </button>
              </form>

              <div className="text-center mt-2 pt-4 border-t border-outline-variant/30">
                {onBackHome && (
                  <button
                    onClick={onBackHome}
                    className="block mb-2 text-body-sm text-outline hover:text-primary transition cursor-pointer"
                  >
                    ← Back to Home
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden"
          >
            <div className="h-2 w-full bg-primary"></div>
            <div className="p-8">
              {!resetSent ? (
                <div className="flex flex-col gap-6">
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-primary-container text-primary mb-4 shadow-sm">
                      <Lock className="w-6 h-6" />
                    </div>
                    <h1 className="font-sans text-h1 text-primary font-semibold mb-2">Forgot Password</h1>
                    <p className="text-body-sm text-on-surface-variant">Enter your email to receive a reset link.</p>
                  </div>
                  <form onSubmit={handleForgotPassword} className="space-y-6">
                    <div className="space-y-2">
                      <label className="block text-xs font-semibold text-on-surface" htmlFor="forgotEmail">Email Address</label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                        <input
                          className="block w-full pl-10 pr-3 py-2.5 border border-outline-variant rounded-lg bg-surface text-on-surface focus:ring-1 focus:ring-primary focus:border-primary transition text-body-sm"
                          id="forgotEmail"
                          placeholder="name@dixpertia.com"
                          required
                          type="email"
                          value={forgotEmail}
                          onChange={(e) => setForgotEmail(e.target.value)}
                        />
                      </div>
                    </div>
                    <button
                      className="w-full flex justify-center items-center py-3 px-4 rounded-lg font-semibold text-white bg-primary hover:bg-primary/95 transition shadow-sm"
                      type="submit"
                    >
                      Send reset link
                    </button>
                  </form>
                </div>
              ) : (
                <div className="text-center space-y-6 py-4">
                  <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-secondary-fixed/30 text-secondary mb-4">
                    <CheckCircle className="w-10 h-10 text-[#137333]" />
                  </div>
                  <h2 className="text-h2 font-semibold text-primary">Check your email</h2>
                  <p className="text-body-sm text-on-surface-variant">
                    We sent a reset link to <br />
                    <span className="font-bold text-on-surface break-all">{forgotEmail}</span>
                  </p>
                  <div className="pt-4 border-t border-outline-variant/30">
                    <p className="text-xs text-on-surface-variant mb-2">Didn't receive it?</p>
                    <button
                      onClick={handleResend}
                      disabled={isResending}
                      className="text-secondary hover:text-primary font-semibold text-body-sm underline transition inline-flex items-center gap-1.5"
                    >
                      {isResending ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        'Resend link'
                      )}
                    </button>
                  </div>
                </div>
              )}
              <div className="mt-8 pt-6 border-t border-outline-variant/30 text-center">
                {onBackHome && (
                  <button
                    onClick={onBackHome}
                    className="block mb-2 text-body-sm text-outline hover:text-primary transition cursor-pointer"
                  >
                    ← Back to Home
                  </button>
                )}
                <button
                  onClick={() => {
                    setResetSent(false);
                    setShowForgot(false);
                  }}
                  className="inline-flex items-center text-body-sm font-semibold text-secondary hover:text-primary transition cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to login
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}