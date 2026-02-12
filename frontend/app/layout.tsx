import type { Metadata } from 'next'
import './globals.css'
import { AppLayout } from '@/components/layout/app-layout'

export const metadata: Metadata = {
  title: 'Ledgerly',
  description: 'Smart Personal Finance Tracker',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  )
}