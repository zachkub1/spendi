'use client';

/**
 * ConnectGmailButton - initiates Gmail OAuth flow for email ingestion.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface ConnectGmailButtonProps {
  onConnected?: () => void;
}

export function ConnectGmailButton({ onConnected }: ConnectGmailButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleConnect = async () => {
    setLoading(true);
    try {
      // Call Gmail-specific OAuth endpoint
      const response = await apiClient.get<{ authorization_url: string }>(
        '/email/auth/login'
      );

      // Redirect to Google OAuth consent screen
      window.location.href = response.authorization_url;
    } catch (error) {
      console.error('Failed to initiate Gmail connection:', error);
      setLoading(false);
    }
  };

  return (
    <Button onClick={handleConnect} disabled={loading}>
      {loading ? 'Connecting...' : 'Connect Gmail Account'}
    </Button>
  );
}
