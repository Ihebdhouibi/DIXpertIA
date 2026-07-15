import React, { useState } from 'react';
import { Mail, Lock, User, ArrowRight, ArrowLeft, CheckCircle, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';
import { UserRole } from '../types';

interface RegistrationProps {
  onLogin: (role: UserRole, email: string, firstName: string, lastName: string) => void;
  onBackHome?: () => void;   // <--- new optional prop
}

type AuthScreen = 'register' | 'login' | 'forgot-password';

export default function Registration({ onLogin, onBackHome }: RegistrationProps) {
  const [screen, setScreen] = useState<AuthScreen>('register');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetSent, setResetSent] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [roleSelection, setRoleSelection] = useState<UserRole>('employee');

  // Register Handler
  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName || !lastName || !email || !password) return;
    // Auto-login with selected role
    onLogin(roleSelection, email, firstName, lastName);
  };

  // Login Handler
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    // Check if admin email for demo purposes
    const selectedRole: UserRole = email.toLowerCase().includes('admin') ? 'admin' : 'employee';
    const displayFirst = firstName || 'User';
    const displayLast = lastName || 'Demo';
    onLogin(selectedRole, email, displayFirst, displayLast);
  };

  // Forgot Password Handler
  const handleForgotPassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail) return;
    setResetSent(true);
  };

  // Resend Handler
  const handleResend = () => {
    setIsResending(true);
    setTimeout(() => {
      setIsResending(false);
    }, 1200);
  };

  // Shortcut/Bypass login for testing convenience
  const handleQuickBypass = (selectedRole: UserRole) => {
    if (selectedRole === 'admin') {
      onLogin('admin', 'admin@dixpertia.com', 'Admin', 'User');
    } else {
      onLogin('employee', 'john.doe@dixpertia.com', 'John', 'Doe');
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-[#e0f2fe] relative overflow-hidden bg-pattern">
      
      {/* Decorative background gradients */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-10">
        <div className="absolute -top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full bg-primary-container/20 blur-3xl"></div>
        <div className="absolute -bottom-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-secondary-fixed/30 blur-3xl"></div>
      </div>

      {/* Main Container */}
      <main className="w-full max-w-[480px] relative z-10">
        
        {/* Role Quick Selector for the Agent Workspace Preview */}
        <div className="mb-4 text-center bg-white/70 backdrop-blur-md rounded-lg p-2.5 border border-outline-variant/30 shadow-sm">
          <p className="text-xs text-on-surface-variant font-semibold mb-2">Quick Demo Access (Workspace Tester):</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => handleQuickBypass('employee')}
              className="px-3 py-1 bg-primary text-white hover:bg-primary/90 text-xs font-semibold rounded shadow-sm transition-colors cursor-pointer"
            >
              Employee Mode (John Doe)
            </button>
            <button
              onClick={() => handleQuickBypass('admin')}
              className="px-3 py-1 bg-secondary text-white hover:bg-secondary/90 text-xs font-semibold rounded shadow-sm transition-colors cursor-pointer"
            >
              Admin HR Mode (Invoices & Team)
            </button>
          </div>
        </div>

        {/* 1. Register Screen */}
        {screen === 'register' && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="bg-white rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden"
          >
            <div className="h-2 w-full bg-primary"></div>
            <div className="p-8 flex flex-col gap-6">
              
              {/* Header */}
              <div className="text-center">
                <div className="font-sans text-h2 font-black text-primary tracking-tight mb-2">DIXpertIA</div>
                <h1 className="font-sans text-h1 text-on-surface font-semibold">Create Account</h1>
                <p className="text-body-sm text-on-surface-variant mt-2">Enter your details to get started.</p>
              </div>

              {/* Form */}
              <form onSubmit={handleRegister} className="flex flex-col gap-4">
                
                {/* Role Switcher in registration for direct role setting */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-on-surface-variant">Desired Role</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setRoleSelection('employee')}
                      className={`py-1.5 px-3 rounded text-xs font-semibold border transition-all cursor-pointer ${
                        roleSelection === 'employee'
                          ? 'bg-primary/10 border-primary text-primary shadow-sm'
                          : 'border-outline-variant text-on-surface-variant bg-white hover:bg-surface-container-low'
                      }`}
                    >
                      Employee
                    </button>
                    <button
                      type="button"
                      onClick={() => setRoleSelection('admin')}
                      className={`py-1.5 px-3 rounded text-xs font-semibold border transition-all cursor-pointer ${
                        roleSelection === 'admin'
                          ? 'bg-primary/10 border-primary text-primary shadow-sm'
                          : 'border-outline-variant text-on-surface-variant bg-white hover:bg-surface-container-low'
                      }`}
                    >
                      HR Admin
                    </button>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-xs font-medium text-on-surface-variant" htmlFor="firstName">First name</label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                      <input
                        className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors text-body-sm text-on-surface placeholder:text-outline-variant"
                        id="firstName"
                        name="firstName"
                        placeholder="John"
                        required
                        type="text"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-xs font-medium text-on-surface-variant" htmlFor="lastName">Last name</label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                      <input
                        className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors text-body-sm text-on-surface placeholder:text-outline-variant"
                        id="lastName"
                        name="lastName"
                        placeholder="Doe"
                        required
                        type="text"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-on-surface-variant" htmlFor="email">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                    <input
                      className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors text-body-sm text-on-surface placeholder:text-outline-variant"
                      id="email"
                      name="email"
                      placeholder="john.doe@example.com"
                      required
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-on-surface-variant" htmlFor="password">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                    <input
                      className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors text-body-sm text-on-surface placeholder:text-outline-variant"
                      id="password"
                      name="password"
                      placeholder="••••••••"
                      required
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                  <p className="text-xs text-outline">Must be at least 8 characters.</p>
                </div>

                <button
                  className="mt-4 w-full bg-primary hover:bg-primary/95 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-sm"
                  type="submit"
                >
                  Create account
                  <ArrowRight className="w-5 h-5" />
                </button>
              </form>

              {/* Footer Links with Back to Home */}
              <div className="text-center mt-2 pt-4 border-t border-outline-variant/30">
                {onBackHome && (
                  <button
                    onClick={onBackHome}
                    className="block mb-2 text-body-sm text-outline hover:text-primary transition-colors cursor-pointer"
                  >
                    ← Back to Home
                  </button>
                )}
                <p className="text-body-sm text-on-surface-variant">
                  Already have an account?{' '}
                  <button
                    onClick={() => setScreen('login')}
                    className="text-primary font-semibold hover:underline hover:text-secondary transition-colors cursor-pointer"
                  >
                    Sign in
                  </button>
                </p>
              </div>

            </div>
          </motion.div>
        )}

        {/* 2. Login Screen */}
        {screen === 'login' && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="bg-white rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden"
          >
            <div className="h-2 w-full bg-primary"></div>
            <div className="p-8 flex flex-col gap-6">

              <div className="text-center">
                <div className="font-sans text-h2 font-black text-primary tracking-tight mb-2">DIXpertIA</div>
                <h1 className="font-sans text-h1 text-on-surface font-semibold">Sign In</h1>
                <p className="text-body-sm text-on-surface-variant mt-2">Access your employee portal dashboard.</p>
              </div>

              <form onSubmit={handleLogin} className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-on-surface-variant" htmlFor="loginEmail">Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                    <input
                      className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors text-body-sm text-on-surface placeholder:text-outline-variant"
                      id="loginEmail"
                      placeholder="name@company.com"
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
                      onClick={() => setScreen('forgot-password')}
                      className="text-xs text-secondary hover:underline cursor-pointer"
                    >
                      Forgot?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                    <input
                      className="w-full bg-white border border-outline-variant rounded-lg py-2 pl-10 pr-3 focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors text-body-sm text-on-surface placeholder:text-outline-variant"
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
                  className="mt-4 w-full bg-primary hover:bg-primary/95 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-sm"
                  type="submit"
                >
                  Sign In
                  <ArrowRight className="w-5 h-5" />
                </button>
              </form>

              {/* Footer Links with Back to Home */}
              <div className="text-center mt-2 pt-4 border-t border-outline-variant/30">
                {onBackHome && (
                  <button
                    onClick={onBackHome}
                    className="block mb-2 text-body-sm text-outline hover:text-primary transition-colors cursor-pointer"
                  >
                    ← Back to Home
                  </button>
                )}
                <p className="text-body-sm text-on-surface-variant">
                  Don't have an account?{' '}
                  <button
                    onClick={() => setScreen('register')}
                    className="text-primary font-semibold hover:underline hover:text-secondary transition-colors cursor-pointer"
                  >
                    Create one
                  </button>
                </p>
              </div>

            </div>
          </motion.div>
        )}

        {/* 3. Forgot Password Screen */}
        {screen === 'forgot-password' && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
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
                    <p className="text-body-sm text-on-surface-variant">Enter your email address to receive a password reset link.</p>
                  </div>

                  <form onSubmit={handleForgotPassword} className="space-y-6">
                    <div className="space-y-2">
                      <label className="block text-xs font-semibold text-on-surface" htmlFor="forgotEmail">Email Address</label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                        <input
                          className="block w-full pl-10 pr-3 py-2.5 border border-outline-variant rounded-lg bg-surface text-on-surface placeholder:text-outline focus:ring-1 focus:ring-primary focus:border-primary transition-all text-body-sm"
                          id="forgotEmail"
                          placeholder="name@company.com"
                          required
                          type="email"
                          value={forgotEmail}
                          onChange={(e) => setForgotEmail(e.target.value)}
                        />
                      </div>
                    </div>
                    
                    <button
                      className="w-full flex justify-center items-center py-3 px-4 rounded-lg font-semibold text-white bg-primary hover:bg-primary/95 transition-all cursor-pointer shadow-sm"
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
                    We have sent a password reset link to <br />
                    <span className="font-bold text-on-surface break-all">{forgotEmail}</span>
                  </p>
                  
                  <div className="pt-4 border-t border-outline-variant/30">
                    <p className="text-xs text-on-surface-variant mb-2">Didn't receive the email? Check your spam folder or</p>
                    <button
                      onClick={handleResend}
                      disabled={isResending}
                      className="text-secondary hover:text-primary font-semibold text-body-sm underline transition-colors cursor-pointer inline-flex items-center gap-1.5"
                    >
                      {isResending ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        'Click here to resend'
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Back to login / Home */}
              <div className="mt-8 pt-6 border-t border-outline-variant/30 text-center">
                {onBackHome && (
                  <button
                    onClick={onBackHome}
                    className="block mb-2 text-body-sm text-outline hover:text-primary transition-colors cursor-pointer"
                  >
                    ← Back to Home
                  </button>
                )}
                <button
                  onClick={() => {
                    setResetSent(false);
                    setScreen('login');
                  }}
                  className="inline-flex items-center text-body-sm font-semibold text-secondary hover:text-primary transition-colors cursor-pointer"
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