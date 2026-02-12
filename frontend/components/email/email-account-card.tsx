'use client';

/**
 * EmailAccountCard - displays connected email account with sync status.
 */

import { useState } from 'react';
import type { EmailAccount } from '@shared/types/email-account';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface EmailAccountCardProps {
  account: EmailAccount;
  onDisconnected?: () => void;
}

export function EmailAccountCard({ account, onDisconnected }: EmailAccountCardProps) {
  const [disconnecting, setDisconnecting] = useState(false);

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect this email account?')) {
      return;
    }

    setDisconnecting(true);
    try {
      await apiClient.delete(`/email/accounts/${account.id}`);
      onDisconnected?.();
    } catch (error) {
      console.error('Failed to disconnect account:', error);
      setDisconnecting(false);
    }
  };

  const getSyncStatusBadge = () => {
    if (!account.sync_status) {
      return <span className="text-xs text-gray-500">Not synced yet</span>;
    }

    const colors = {
      success: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
    };

    return (
      <span className={`text-xs px-2 py-1 rounded ${colors[account.sync_status]}`}>
        {account.sync_status === 'in_progress' ? 'Syncing...' : account.sync_status}
      </span>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center justify-between">
          <span>{account.email_address}</span>
          {getSyncStatusBadge()}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-sm text-gray-600">
          <p>Provider: {account.provider}</p>
          {account.last_sync_at && (
            <p>Last synced: {new Date(account.last_sync_at).toLocaleString()}</p>
          )}
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleDisconnect}
          disabled={disconnecting}
        >
          {disconnecting ? 'Disconnecting...' : 'Disconnect'}
        </Button>
      </CardContent>
    </Card>
  );
}
