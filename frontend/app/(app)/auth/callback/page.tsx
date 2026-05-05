'use client';

/**
 * OAuth callback page - handles redirect from Google OAuth.
 * Extracts token from URL fragment (#token=...), stores it, fetches user info,
 * and redirects to dashboard.
 *
 * The token arrives in the URL fragment rather than a query param so it is
 * never sent to the server (no logs, no Referer header exposure).
 */

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

function CallbackContent() {
  const router = useRouter();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      // Extract token from URL fragment — never sent to the server.
      // window.location.hash is "#token=<jwt>"; slice(1) removes the leading '#'.
      const fragment = window.location.hash.slice(1);
      const params = new URLSearchParams(fragment);
      const token = params.get('token');

      if (!token) {
        setError('No authentication token received');
        return;
      }

      try {
        await login(token);
        router.push('/dashboard');
      } catch (err) {
        console.error('Authentication failed:', err);
        setError('Authentication failed. Please try again.');
      }
    };

    handleCallback();
  }, [login, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Authentication Error</h1>
          <p className="mt-2 text-gray-600">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
        <p className="mt-4 text-lg text-gray-600">Completing sign in...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
