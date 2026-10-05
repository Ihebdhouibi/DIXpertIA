import React from 'react';
import { motion } from 'motion/react';

/**
 * Shared frame for Login, ForgotPassword and ResetPassword (#29): the app's
 * ground, one centred card with the wordmark and a hairline-separated footer.
 * Flat on purpose - the old blurred blobs and dot grid were M3 decoration.
 */
interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

export default function AuthLayout({ title, subtitle, footer, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-background text-on-surface">
      <main className="w-full max-w-[440px]">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-sm"
        >
          <div className="p-8 flex flex-col gap-6">
            <div className="flex flex-col gap-5">
              <span className="inline-flex items-center gap-2" aria-label="DI Xpertia">
                <img src="/brand/mark-dark.svg" alt="" className="w-8 h-8 dark:hidden" />
                <img src="/brand/mark-light.svg" alt="" className="w-8 h-8 hidden dark:block" />
                <span className="text-lg font-bold tracking-[-0.02em]" aria-hidden="true">
                  DI <span className="font-mono font-medium text-secondary">Xpertia</span>
                </span>
              </span>
              <div>
                <h1 className="text-2xl font-bold tracking-[-0.02em]">{title}</h1>
                {subtitle && <p className="mt-1.5 text-sm text-on-surface-variant">{subtitle}</p>}
              </div>
            </div>
            {children}
          </div>
          {footer && <div className="px-8 py-4 border-t border-outline-variant">{footer}</div>}
        </motion.div>
      </main>
    </div>
  );
}
