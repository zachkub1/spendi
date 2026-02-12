/**
 * Login page - public route for unauthenticated users.
 * Displays Ledgerly branding and Sign in with Google button.
 */

import { LoginButton } from '@/components/auth/login-button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">Ledgerly</CardTitle>
          <CardDescription className="text-base">
            Smart Personal Finance Tracker
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center space-y-4">
          <p className="text-center text-sm text-gray-600">
            Sign in to start tracking your finances with automated email ingestion and
            smart insights.
          </p>
          <LoginButton />
        </CardContent>
      </Card>
    </div>
  );
}
