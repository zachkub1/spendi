'use client';

/**
 * FeedbackButton — nav bar button that opens the FeedbackModal.
 * Only rendered when a user is authenticated (useAuth().user is non-null).
 */

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { FeedbackModal } from './feedback-modal';

export function FeedbackButton() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-colors"
        aria-label="Send feedback"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
          />
        </svg>
        Feedback
      </button>

      <FeedbackModal isOpen={open} onClose={() => setOpen(false)} />
    </>
  );
}
