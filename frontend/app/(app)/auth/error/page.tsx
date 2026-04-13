'use client';

/**
 * OAuth error page - displays OAuth error messages.
 * Shown when OAuth flow fails or is cancelled.
 */

import { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

function ErrorContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const message = searchParams.get('message') || 'An error occurred during authentication';

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center text-red-600">Authentication Error</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-gray-700">{message}</p>
          <div className="flex justify-center">
            <Button onClick={() => router.push('/login')}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
      </div>
    }>
      <ErrorContent />
    </Suspense>
  );
}
