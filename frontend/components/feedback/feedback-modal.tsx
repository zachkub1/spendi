'use client';

/**
 * FeedbackModal — form for submitting bugs, suggestions, and classification issues.
 *
 * Security:
 *  - No dangerouslySetInnerHTML anywhere in this component.
 *  - All values submitted as JSON; the API client escapes nothing because
 *    the backend sanitizes on ingestion.
 *  - Form validates client-side before any network call.
 */

import { useState, useRef, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

// ── Types ─────────────────────────────────────────────────────────────────────

type FeedbackType = 'bug' | 'suggestion' | 'classification_issue';

interface FeedbackPayload {
  type: FeedbackType;
  message: string;
  transaction_example?: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const TYPES: { value: FeedbackType; label: string; description: string }[] = [
  { value: 'bug', label: 'Bug', description: 'Something is broken or not working' },
  { value: 'suggestion', label: 'Suggestion', description: 'Feature or improvement idea' },
  {
    value: 'classification_issue',
    label: 'Classification Issue',
    description: 'Wrong category, bank, or card match',
  },
];

const MAX_MESSAGE = 5000;
const MAX_EXAMPLE = 10000;

// ── Component ─────────────────────────────────────────────────────────────────

export function FeedbackModal({ isOpen, onClose }: Props) {
  const [type, setType] = useState<FeedbackType>('bug');
  const [message, setMessage] = useState('');
  const [transactionExample, setTransactionExample] = useState('');
  const [errors, setErrors] = useState<Partial<Record<'message' | 'transactionExample', string>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const firstInputRef = useRef<HTMLTextAreaElement>(null);

  // Focus first field when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => firstInputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setType('bug');
      setMessage('');
      setTransactionExample('');
      setErrors({});
      setSuccess(false);
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // ── Validation ──────────────────────────────────────────────────────────────

  function validate(): boolean {
    const next: typeof errors = {};

    if (!message.trim()) {
      next.message = 'Description is required.';
    } else if (message.length > MAX_MESSAGE) {
      next.message = `Description must be under ${MAX_MESSAGE.toLocaleString()} characters.`;
    }

    if (type === 'classification_issue' && !transactionExample.trim()) {
      next.transactionExample = 'Please paste the transaction email or description.';
    } else if (transactionExample.length > MAX_EXAMPLE) {
      next.transactionExample = `Example must be under ${MAX_EXAMPLE.toLocaleString()} characters.`;
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  }

  // ── Submit ──────────────────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      const body: FeedbackPayload = { type, message: message.trim() };
      if (type === 'classification_issue' && transactionExample.trim()) {
        body.transaction_example = transactionExample.trim();
      }
      await apiClient.post('/feedback', body);
      setSuccess(true);
      // Auto-close after showing success state
      setTimeout(onClose, 1800);
    } catch (err) {
      setErrors({ message: 'Failed to submit feedback. Please try again.' });
    } finally {
      setSubmitting(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(15,23,42,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-modal-title"
    >
      {/* Panel */}
      <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-slate-100">
          <div>
            <h2 id="feedback-modal-title" className="text-lg font-semibold text-slate-900">
              Send Feedback
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Help us improve Spendi
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close feedback"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Success state */}
        {success ? (
          <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
            <div className="h-14 w-14 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
              <svg className="h-7 w-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-slate-900">Feedback submitted!</p>
            <p className="text-sm text-slate-500 mt-1">Thanks for helping make Spendi better.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <div className="px-6 py-5 space-y-5">

              {/* Type selector */}
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Type</p>
                <div className="grid grid-cols-3 gap-2">
                  {TYPES.map((t) => (
                    <button
                      key={t.value}
                      type="button"
                      onClick={() => {
                        setType(t.value);
                        // Clear classification example when switching away
                        if (t.value !== 'classification_issue') {
                          setTransactionExample('');
                          setErrors((prev) => ({ ...prev, transactionExample: undefined }));
                        }
                      }}
                      className={`flex flex-col items-start p-3 rounded-xl border-2 text-left transition-all ${
                        type === t.value
                          ? 'border-indigo-500 bg-indigo-50'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <span className={`text-xs font-semibold ${type === t.value ? 'text-indigo-700' : 'text-slate-700'}`}>
                        {t.label}
                      </span>
                      <span className="text-xs text-slate-400 mt-0.5 leading-snug">{t.description}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Description */}
              <div>
                <label htmlFor="feedback-message" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="feedback-message"
                  ref={firstInputRef}
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    if (errors.message) setErrors((prev) => ({ ...prev, message: undefined }));
                  }}
                  rows={4}
                  maxLength={MAX_MESSAGE}
                  placeholder={
                    type === 'bug'
                      ? 'Describe what happened and what you expected…'
                      : type === 'suggestion'
                      ? 'Describe your idea or requested improvement…'
                      : 'Describe the misclassification (e.g. "Uber Eats categorized as Transportation")…'
                  }
                  className={`w-full px-3 py-2.5 text-sm rounded-lg border resize-none focus:outline-none focus:ring-2 transition-colors ${
                    errors.message
                      ? 'border-red-400 focus:ring-red-400'
                      : 'border-slate-300 focus:ring-indigo-500'
                  }`}
                />
                <div className="flex items-center justify-between mt-1">
                  {errors.message ? (
                    <p className="text-xs text-red-600">{errors.message}</p>
                  ) : (
                    <span />
                  )}
                  <span className="text-xs text-slate-400 ml-auto">
                    {message.length}/{MAX_MESSAGE.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Transaction example — conditional */}
              {type === 'classification_issue' && (
                <div>
                  <label htmlFor="feedback-example" className="block text-sm font-medium text-slate-700 mb-1.5">
                    Transaction email / description <span className="text-red-500">*</span>
                  </label>
                  <p className="text-xs text-slate-500 mb-2">
                    Paste the raw email text or transaction description to help us improve parsing accuracy.
                  </p>
                  <textarea
                    id="feedback-example"
                    value={transactionExample}
                    onChange={(e) => {
                      setTransactionExample(e.target.value);
                      if (errors.transactionExample) {
                        setErrors((prev) => ({ ...prev, transactionExample: undefined }));
                      }
                    }}
                    rows={5}
                    maxLength={MAX_EXAMPLE}
                    placeholder="Paste the transaction email body or description here…"
                    className={`w-full px-3 py-2.5 text-sm rounded-lg border resize-none font-mono focus:outline-none focus:ring-2 transition-colors ${
                      errors.transactionExample
                        ? 'border-red-400 focus:ring-red-400'
                        : 'border-slate-300 focus:ring-indigo-500'
                    }`}
                  />
                  <div className="flex items-center justify-between mt-1">
                    {errors.transactionExample ? (
                      <p className="text-xs text-red-600">{errors.transactionExample}</p>
                    ) : (
                      <span />
                    )}
                    <span className="text-xs text-slate-400 ml-auto">
                      {transactionExample.length}/{MAX_EXAMPLE.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {submitting && (
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                )}
                {submitting ? 'Submitting…' : 'Submit Feedback'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
