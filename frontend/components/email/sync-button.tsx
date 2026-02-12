'use client';

/**
 * SyncButton - triggers manual email sync.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface SyncButtonProps {
  accountId: string;
  onSyncComplete?: () => void;
}

export function SyncButton({ accountId, onSyncComplete }: SyncButtonProps) {
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await apiClient.post(`/email/sync/${accountId}`);

      // Poll for completion after 5 seconds (simple approach)
      setTimeout(() => {
        setSyncing(false);
        onSyncComplete?.();
      }, 5000);
    } catch (error) {
      console.error('Sync failed:', error);
      setSyncing(false);
    }
  };

  return (
    <Button onClick={handleSync} disabled={syncing} size="sm">
      {syncing ? 'Syncing...' : 'Sync Emails'}
    </Button>
  );
}
