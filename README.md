# Spendi

**Smart personal finance tracking, zero manual entry.**

Spendi connects to your Gmail and automatically finds transaction confirmation emails from your bank and credit cards. Every purchase, transfer, and payment is parsed, categorized, and shown in a clean dashboard so you always know where your money is going.

---

## What Spendi does

- **Reads your transaction emails** — Spendi scans your Gmail for bank and card notifications and extracts the amount, merchant, and date automatically.
- **Categorizes spending** — purchases are tagged (Food, Transport, Shopping, etc.) so you can see spending by category at a glance.
- **Tracks across all your cards** — see every account in one place without linking bank credentials.
- **Shows spending trends** — month-over-month breakdowns help you spot where your budget is slipping.
- **Privacy-first** — Spendi only reads transaction confirmation emails. It never stores your Gmail password; it uses Google's secure OAuth flow and only requests read access.

---

## Getting started

**1. Go to [spendi.live](https://spendi.live)**

**2. Click "Continue with Google"**

Sign in with the Gmail account that receives your bank and credit card notifications. Google's standard permission screen will ask for read-only Gmail access — Spendi uses this only to find transaction emails.

**3. That's it**

Spendi syncs your emails in the background. Within a minute or two your recent transactions will appear on the dashboard. New transaction emails are picked up automatically going forward.

---

## Privacy & security

- Spendi requests **Gmail read-only** access — it cannot send, delete, or modify any email.
- Your OAuth tokens are encrypted at rest using AES-256.
- No bank credentials, card numbers, or passwords are ever stored.
- All traffic is encrypted in transit via HTTPS/TLS.
- You can revoke Spendi's Gmail access at any time from your [Google Account permissions page](https://myaccount.google.com/permissions).

---

## Supported email sources

Spendi currently recognises transaction notification emails from most major US banks and card issuers, including Chase, Bank of America, Capital One, Citi, American Express, Wells Fargo, and Venmo/Cash App P2P transfers. Support for additional senders is added continuously.

---

## Feedback & issues

Found a bug or want a feature? Open an issue on [GitHub](https://github.com/zachkub1/spendi/issues).
