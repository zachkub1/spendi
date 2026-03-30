'use client';

/**
 * DemoSyncButton - injects mock email data without real Gmail access.
 * Calls POST /email/demo-sync which runs mocked emails through the real parser pipeline.
 * Idempotent: re-clicking reports already-loaded count instead of duplicating.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface DemoSyncResult {
  message: string;
  parsed: number;
  non_transaction: number;
  already_exists: number;
}

interface DemoSyncButtonProps {
  onSyncComplete?: () => void;
}

export function DemoSyncButton({ onSyncComplete }: DemoSyncButtonProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DemoSyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDemoSync = async () => {
    setLoading(true);
    setResult(null);
    setError(null);

    console.log('[DemoSync] Starting demo email injection...');

    try {
      const data = await apiClient.post<DemoSyncResult>('/email/demo-sync');

      console.log('[DemoSync] Result:', data);
      setResult(data);
      onSyncComplete?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Demo sync failed';
      console.error('[DemoSync] Error:', err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const statusMessage = () => {
    if (!result) return null;
    if (result.parsed > 0) {
      return `${result.parsed} new transaction${result.parsed !== 1 ? 's' : ''} loaded`;
    }
    if (result.already_exists > 0) {
      return `Demo data already loaded (${result.already_exists} emails)`;
    }
    return 'Demo sync complete';
  };

  return (
    <div className="space-y-1">
      <Button
        onClick={handleDemoSync}
        disabled={loading}
        variant="outline"
        size="sm"
        className="text-gray-600 border-dashed"
      >
        {loading ? 'Loading demo data…' : '⚡ Load Demo Transactions'}
      </Button>

      {result && (
        <p className="text-xs text-green-600">{statusMessage()}</p>
      )}
      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}
    </div>
  );
}
