'use client';

/**
 * Gmail OAuth callback page - handles redirect from Google OAuth for email connection.
 */

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [hasProcessed, setHasProcessed] = useState(false);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');

      if (!code) {
        setError('No authorization code received');
        return;
      }

      // Prevent duplicate calls - check if we've already processed ANY code
      if (hasProcessed) {
        console.log('Already processed a code, skipping');
        return;
      }

      // Mark as processed immediately to prevent any duplicate calls
      setHasProcessed(true);

      try {
        console.log('Exchanging OAuth code for tokens...');
        console.log('Code (first 20 chars):', code.substring(0, 20) + '...');

        // Send code to backend to exchange for tokens
        await apiClient.post('/email/connect', { code });

        console.log('Successfully connected Gmail account');
        // Redirect back to email page
        router.push('/email');
      } catch (err: any) {
        console.error('Failed to connect Gmail:', err);
        console.error('Full error details:', JSON.stringify(err, null, 2));
        const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to connect Gmail account';

        // Special handling for code reuse error
        if (errorMessage.includes('already been used')) {
          setError('This authorization has expired. Please try connecting again from the email settings page.');
        } else {
          setError(`Failed to connect Gmail: ${errorMessage}. Check browser console for details.`);
        }

        // Don't reset hasProcessed on error - we still processed this code
      }
    };

    handleCallback();
  }, [searchParams, router, hasProcessed]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Connection Error</h1>
          <p className="mt-2 text-gray-600">{error}</p>
          <button
            onClick={() => router.push('/email')}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            Back to Email Settings
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
        <p className="mt-4 text-lg text-gray-600">Connecting Gmail account...</p>
      </div>
    </div>
  );
}

export default function EmailCallbackPage() {
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
