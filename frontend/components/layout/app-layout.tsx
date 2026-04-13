'use client';

/**
 * AppLayout - client component wrapper for AuthProvider and app header.
 * Wraps the entire app to provide auth context and consistent header.
 */

import Link from 'next/link';
import { AuthProvider } from '@/lib/auth-context';
import { UserMenu } from './user-menu';
import { FeedbackButton } from '@/components/feedback/feedback-button';

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-slate-50">
        <header className="bg-white border-b border-slate-200">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link href="/dashboard" className="text-xl font-bold text-indigo-700 hover:text-indigo-900 transition-colors">
                Ledgerly
              </Link>
              <nav className="flex items-center gap-4 text-sm font-medium">
                <Link href="/transactions" className="text-slate-600 hover:text-indigo-700 transition-colors">
                  Transactions
                </Link>
                <Link href="/insights" className="text-slate-600 hover:text-indigo-700 transition-colors">
                  Insights
                </Link>
                <Link href="/email" className="text-slate-600 hover:text-indigo-700 transition-colors">
                  Email
                </Link>
                <Link href="/cards" className="text-slate-600 hover:text-indigo-700 transition-colors">
                  Card Manager
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-2">
              <FeedbackButton />
              <UserMenu />
            </div>
          </div>
        </header>
        <main>{children}</main>
      </div>
    </AuthProvider>
  );
}
