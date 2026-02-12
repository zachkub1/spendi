'use client';

/**
 * Dashboard page - main protected route after login.
 * Shows welcome message and placeholder for future features.
 */

import { ProtectedRoute } from '@/components/auth/protected-route';
import { useAuth } from '@/lib/auth-context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">
          Welcome, {user?.display_name || user?.email || 'User'}
        </h1>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Email Integration</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Connect your Gmail account to automatically ingest financial transactions.
              </p>
              <p className="text-sm text-gray-500 mt-2">Coming in Week 2</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Transactions</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                View all your parsed transactions from email receipts.
              </p>
              <p className="text-sm text-gray-500 mt-2">Coming in Week 3</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Get smart spending insights and rewards optimization.
              </p>
              <p className="text-sm text-gray-500 mt-2">Coming in Phase 2</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  );
}
