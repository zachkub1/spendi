'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AuthProvider } from '@/lib/auth-context';
import { UserMenu } from './user-menu';
import { FeedbackButton } from '@/components/feedback/feedback-button';

const NAV_LINKS = [
  { href: '/transactions', label: 'Transactions' },
  { href: '/insights', label: 'Insights' },
  { href: '/email', label: 'Email' },
  { href: '/cards', label: 'Card Manager' },
];

function NavLinks({ onClick }: { onClick?: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {NAV_LINKS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          onClick={onClick}
          className={`text-sm font-medium transition-colors hover:text-indigo-700 ${
            pathname.startsWith(href) ? 'text-indigo-700' : 'text-slate-600'
          }`}
        >
          {label}
        </Link>
      ))}
    </>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <AuthProvider>
      <div className="min-h-screen bg-slate-50">
        <header className="bg-white border-b border-slate-200">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            {/* Logo */}
            <Link
              href="/dashboard"
              className="text-xl font-bold text-indigo-700 hover:text-indigo-900 transition-colors flex-shrink-0"
            >
              Spendi
            </Link>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-4 ml-6">
              <NavLinks />
            </nav>

            {/* Right side */}
            <div className="flex items-center gap-2 ml-auto">
              <FeedbackButton />
              <UserMenu />

              {/* Hamburger — mobile only */}
              <button
                className="md:hidden ml-1 p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
                onClick={() => setMenuOpen((o) => !o)}
                aria-label={menuOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={menuOpen}
              >
                {menuOpen ? (
                  /* X icon */
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  /* Hamburger icon */
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Mobile nav drawer */}
          {menuOpen && (
            <nav className="md:hidden border-t border-slate-100 px-4 py-3 flex flex-col gap-3 bg-white">
              <NavLinks onClick={() => setMenuOpen(false)} />
            </nav>
          )}
        </header>

        <main>{children}</main>
      </div>
    </AuthProvider>
  );
}
