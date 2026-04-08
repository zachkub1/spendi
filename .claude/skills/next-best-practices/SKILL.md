---
name: next-best-practices
description: Enforces Next.js 14 App Router best practices including server/client component boundaries, routing, layouts, metadata, data fetching, and deployment patterns. Use when writing Next.js pages, layouts, API routes, middleware, or when the user mentions App Router, server actions, streaming, or Next.js routing.
license: MIT
compatibility: Designed for Claude Code. Requires Next.js 14+ with App Router.
metadata:
  project: ledgerly
  stack: Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui
---

# Next.js 14 App Router Best Practices

## Server vs Client Components
- Default to **server components**. Add `"use client"` only when you need browser APIs, React hooks, or event handlers.
- Never import server-only utilities (DB, filesystem, secrets) into client components.
- Pass serializable data (plain objects, not class instances) from server to client components via props.
- Use `server-only` package to guard server utilities from client imports.

## App Router Conventions
- Every route segment (`app/*/page.tsx`) is a server component by default.
- Use `layout.tsx` for shared UI that persists across route changes (navigation, auth wrappers).
- Use `loading.tsx` for route-level Suspense loading states.
- Use `error.tsx` as error boundaries for route segments.
- Use `not-found.tsx` for 404 handling within segments.

## Data Fetching
- Fetch data directly in async server components — no `useEffect` or `useState` for server data.
- Use `fetch()` with Next.js caching options (`{ cache: "no-store" }` for dynamic, `{ next: { revalidate: 60 } }` for ISR) in server components.
- For client-side data, use `apiClient` from `frontend/lib/api-client.ts`. Never use raw `fetch()` with `credentials: "include"`.
- Parallel-fetch independent data with `Promise.all` in server components.

## Routing
- Use `useRouter` (from `next/navigation`) in client components for programmatic navigation.
- Prefer `<Link>` over `<a>` for all internal navigation.
- Dynamic segments use `[param]` folders; catch-all use `[...param]`.
- Use `redirect()` (from `next/navigation`) in server components for server-side redirects.

## Performance
- Use `next/image` for all images — it handles optimization, lazy loading, and responsive sizing.
- Use `next/font` for fonts — eliminates FOUT and serves fonts from the same origin.
- Use `next/dynamic` with `{ ssr: false }` for client-only components (charts, maps).
- Split large bundles with dynamic imports. Analyze with `ANALYZE=true next build`.

## Metadata
- Define `metadata` export (static) or `generateMetadata` (dynamic) in every `page.tsx`.
- Include `title`, `description`, and OpenGraph data.

## Ledgerly-Specific Rules
- Auth is JWT-based. Protected pages must check auth via the auth context — no cookie-based auth.
- The `apiClient` in `frontend/lib/api-client.ts` is the ONLY approved method for backend calls.
- Category values sent to the backend must be lowercase strings matching the backend enum exactly.
