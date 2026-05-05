'use client';

/**
 * Login page - full-bleed Spline 3D background with frosted-glass card.
 */

import { useState } from 'react';
import Spline from '@splinetool/react-spline/next';
import { apiClient } from '@/lib/api-client';

function GoogleIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<{ authorization_url: string; state: string }>(
        '/auth/login'
      );
      window.location.href = response.authorization_url;
    } catch {
      setError('Failed to initiate login. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden">

      {/* ── Full-bleed Spline 3D background ───────────────────────────────── */}
      <div className="absolute inset-0 pointer-events-none">
        <Spline scene="https://prod.spline.design/od8n5uOYqkqQ4NJy/scene.splinecode" />
      </div>

      {/* ── Frosted-glass login card ───────────────────────────────────────── */}
      <div className="relative z-10 w-full max-w-sm mx-4">
        <div
          className="rounded-3xl p-8 shadow-2xl"
          style={{
            background: 'rgba(255, 255, 255, 0.55)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(255,255,255,0.7)',
          }}
        >
          {/* Logo / wordmark */}
          <div className="mb-8 text-center">
            <div
              className="inline-flex h-14 w-14 items-center justify-center rounded-2xl mb-4 shadow-lg"
              style={{
                background: 'linear-gradient(135deg, #6366f1 0%, #3b82f6 50%, #06b6d4 100%)',
              }}
            >
              <svg className="h-7 w-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-800">Spendi</h1>
            <p className="mt-1 text-sm text-slate-500">Smart Personal Finance Tracker</p>
          </div>

          {/* Value props */}
          <ul className="mb-8 space-y-2.5">
            {[
              { text: 'Auto-parse transaction emails' },
              { text: 'Spending insights & trends' },
              { text: 'Track across all your cards' },
            ].map(({text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-slate-600">
                {text}
              </li>
            ))}
          </ul>

          {/* Sign-in button */}
          <button
            onClick={handleLogin}
            disabled={loading}
            className="flex w-full items-center justify-center gap-3 rounded-xl px-4 py-3.5 text-sm font-semibold text-slate-700 shadow-md transition-all duration-150 hover:shadow-lg active:scale-[0.98] disabled:opacity-60"
            style={{
              background: 'rgba(255,255,255,0.85)',
              border: '1px solid rgba(99,102,241,0.25)',
            }}
          >
            <GoogleIcon />
            {loading ? 'Redirecting…' : 'Continue with Google'}
          </button>

          {error && (
            <p className="mt-3 text-center text-xs text-red-500">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
