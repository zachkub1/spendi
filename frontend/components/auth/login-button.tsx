'use client';

/**
 * LoginButton component - initiates Google OAuth flow.
 * Calls backend /auth/login to get authorization URL and redirects user.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

export function LoginButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      // Call backend to get Google OAuth authorization URL
      const response = await apiClient.get<{ authorization_url: string; state: string }>(
        '/auth/login'
      );

      // Redirect to Google OAuth consent screen
      window.location.href = response.authorization_url;
    } catch (err) {
      setError('Failed to initiate login. Please try again.');
      setLoading(false);
      console.error('Login error:', err);
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <Button onClick={handleLogin} disabled={loading} size="lg">
        {loading ? 'Loading...' : 'Sign in with Google'}
      </Button>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
