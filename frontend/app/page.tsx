'use client';

import Image from 'next/image';
import Link from 'next/link';

// ─── Navbar ───────────────────────────────────────────────────────────────────

function Navbar() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4"
      style={{
        background: 'rgba(255,255,255,0.15)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255,255,255,0.25)',
      }}
    >
      {/* Wordmark */}
      <div className="flex items-center gap-2.5">
        <div
          className="h-8 w-8 rounded-lg flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #3b82f6 50%, #06b6d4 100%)',
          }}
        >
          <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
          </svg>
        </div>
        <span className="text-lg font-bold text-indigo-900 drop-shadow-sm">Ledgerly</span>
      </div>

      {/* Nav links + CTA */}
      <div className="flex items-center gap-3">
        <a
          href="#about"
          className="hidden sm:block text-sm font-medium text-indigo-900 hover:text-indigo-500 transition-colors px-3 py-1.5"
        >
          About
        </a>
        <a
          href="#features"
          className="hidden sm:block text-sm font-medium text-indigo-900 hover:text-indigo-500 transition-colors px-3 py-1.5"
        >
          Features
        </a>
        <Link
          href="/login"
          className="text-sm font-medium text-indigo-900 hover:text-indigo-500 transition-colors px-4 py-2 rounded-lg"
          style={{ background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)' }}
        >
          Log in
        </Link>
        <Link
          href="/login"
          className="text-sm font-semibold text-indigo-900 px-4 py-2 rounded-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
          style={{ background: 'rgba(255,255,255,0.9)', border: '1px solid rgba(255,255,255,1)' }}
        >
          Sign up free
        </Link>
      </div>
    </nav>
  );
}

// ─── Feature card ─────────────────────────────────────────────────────────────

function FeatureCard({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div
      className="rounded-2xl p-6"
      style={{
        background: 'rgba(255,255,255,0.18)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.35)',
      }}
    >
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="text-base font-semibold text-white mb-1.5">{title}</h3>
      <p className="text-sm text-white/70 leading-relaxed">{body}</p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-hidden">

      {/* ── Background image ──────────────────────────────────────────────── */}
      <Image
        src="/login-bg.png"
        alt=""
        fill
        priority
        className="object-cover object-center"
        sizes="100vw"
      />

      {/* ── Overlay gradient ──────────────────────────────────────────────── */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/60 via-blue-800/40 to-sky-700/50" />

      {/* ── Navbar ────────────────────────────────────────────────────────── */}
      <Navbar />

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative z-10 flex flex-col items-center justify-center text-center min-h-screen px-6 pt-24 pb-16">
        {/* Badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold text-white/90 mb-6"
          style={{ background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)' }}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Privacy-first · No third-party sharing · Your data stays yours
        </div>

        <h1 className="text-5xl sm:text-6xl font-extrabold text-white leading-tight tracking-tight drop-shadow-lg max-w-3xl">
          Your finances,{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{ backgroundImage: 'linear-gradient(90deg, #a5b4fc, #67e8f9)' }}
          >
            on autopilot.
          </span>
        </h1>

        <p className="mt-6 text-lg text-white/75 max-w-xl leading-relaxed">
          Ledgerly connects to your Gmail and automatically extracts transactions from
          any transactional data, Venmo, Zelle and more. No manual entry, no spreadsheets.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <Link
            href="/login"
            className="px-8 py-3.5 rounded-xl text-sm font-bold text-indigo-900 shadow-xl transition-all hover:scale-[1.03] active:scale-[0.97]"
            style={{ background: 'rgba(255,255,255,0.95)' }}
          >
            Get started for free →
          </Link>
          <a
            href="#about"
            className="px-8 py-3.5 rounded-xl text-sm font-semibold text-white transition-all hover:bg-white/10"
            style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.25)' }}
          >
            Learn more
          </a>
        </div>

        {/* Scroll cue */}
        <div className="mt-16 animate-bounce text-white/50">
          <svg className="h-5 w-5 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </section>

      {/* ── About ─────────────────────────────────────────────────────────── */}
      <section
        id="about"
        className="relative z-10 py-24 px-6"
      >
        <div className="max-w-4xl mx-auto">
          <div
            className="rounded-3xl p-10 sm:p-14"
            style={{
              background: 'rgba(255,255,255,0.12)',
              backdropFilter: 'blur(32px)',
              WebkitBackdropFilter: 'blur(32px)',
              border: '1px solid rgba(255,255,255,0.25)',
            }}
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-200 mb-4">
              Why I built this
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-white leading-snug mb-6">
              Tired of having{' '}
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: 'linear-gradient(90deg, #c7d2fe, #7dd3fc)' }}
              >
                to manually log my spending.
              </span>
            </h2>
            <div className="space-y-4 text-white/75 leading-relaxed text-base">
              <p>
                I kept multiple credit cards from different banks, and used Venmo
                and Zelle regularly. Every month I'd open my different bank apps, to 
                see which card I used where and see values larger than my spent due 
                to paying the bill then getting reimbursed by friends. 
              </p>
              <p>
                Existing apps like Mint asked for bank credentials, had intrusive ads,
                and shares data with partners. Spreadsheets required manual entry every
                single time. Neither felt right for something as sensitive as financial data.
              </p>
              <p>
                So I built Ledgerly. It reads the transaction emails your bank already sends
                you, parses them automatically, and organizes everything into a clean
                dashboard — without ever seeing your banking credentials. Your data lives in
                your own database, on your terms.
              </p>
              <p className="text-white/90 font-medium">
                The goal is simple: give every transaction a category, a story, and a trend
                line so you can make smarter decisions with 30 seconds of attention instead
                of 30 minutes of frustration.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────────────────── */}
      <section id="features" className="relative z-10 py-16 px-6 pb-28">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-xs font-semibold uppercase tracking-widest text-indigo-200 mb-3">
            What it does
          </p>
          <h2 className="text-center text-3xl font-bold text-white mb-10">
            Everything you need, nothing you don't
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <FeatureCard
              icon="📧"
              title="Email parsing"
              body="Connects to Gmail and auto-extracts transactions from Chase, Discover, Amex, Venmo, and Zelle notification emails."
            />
            <FeatureCard
              icon="🏷️"
              title="Smart categorization"
              body="Every transaction is automatically categorized — Dining, Travel, Gas, Groceries and 11 more. Override any category in one click."
            />
            <FeatureCard
              icon="📊"
              title="Spending insights"
              body="Monthly and yearly charts show where your money goes, with reimbursement tracking so P2P payments don't skew the numbers."
            />
            <FeatureCard
              icon="💳"
              title="Multi-card support"
              body="Track all your cards in one place. Transactions are automatically matched to the right card by last-4 digits."
            />
            <FeatureCard
              icon="🔒"
              title="Privacy first"
              body="No bank credentials. No third-party sharing. Transactions are parsed from emails you already receive, stored in your own database."
            />
            <FeatureCard
              icon="⚡"
              title="Always up to date"
              body="Background sync runs automatically. New transactions from your latest emails appear without lifting a finger."
            />
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        className="relative z-10 text-center py-8 px-6"
        style={{ borderTop: '1px solid rgba(255,255,255,0.15)' }}
      >
        <p className="text-sm text-white/40">
          © {new Date().getFullYear()} Ledgerly · Built with privacy in mind
        </p>
      </footer>
    </div>
  );
}
