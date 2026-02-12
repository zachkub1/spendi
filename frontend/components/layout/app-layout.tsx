'use client';

/**
 * AppLayout - client component wrapper for AuthProvider and app header.
 * Wraps the entire app to provide auth context and consistent header.
 */

import { AuthProvider } from '@/lib/auth-context';
import { UserMenu } from './user-menu';

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">Ledgerly</h1>
            </div>
            <div className="flex items-center">
              <UserMenu />
            </div>
          </div>
        </header>
        <main>{children}</main>
      </div>
    </AuthProvider>
  );
}
