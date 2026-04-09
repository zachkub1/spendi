---
name: react-best-practices
description: Enforces React best practices including hooks rules, component design, state management, and performance patterns. Use when writing or reviewing React components, hooks, context providers, or when the user mentions React state, effects, memoization, or component architecture.
license: MIT
compatibility: Designed for Claude Code. Requires React 18+ knowledge.
metadata:
  project: ledgerly
  stack: React 18, Next.js 14 App Router, TypeScript, shadcn/ui, Tailwind
---

# React Best Practices

## Component Design
- Prefer small, focused components (< 150 lines). Extract sub-components when a component handles multiple concerns.
- Use named exports for all components. Avoid default exports except for Next.js page files.
- Co-locate component-specific types in the same file.
- Destructure props at the function signature for readability.

## Hooks Rules
- Never call hooks conditionally or inside loops — always at the top level.
- `useEffect` must declare all dependencies in the dependency array. Prefer derivation over effects.
- Use `useCallback` and `useMemo` only when there is a measurable perf benefit or referential stability is required (e.g., a callback passed to a memoized child).
- Custom hooks must be prefixed with `use` and must only call other hooks.
- Extract complex side-effect logic into custom hooks (e.g., `useTransactions`, `useAuth`).

## State Management
- Prefer local state (`useState`) by default. Lift state only when multiple components need it.
- Use React Context only for low-frequency global values (auth, theme). Never put high-frequency update data in Context.
- For server data fetching, prefer server components (Next.js App Router) or SWR/React Query over manual `useEffect` + `useState` fetches.

## Performance
- Wrap expensive pure computations in `useMemo`. Wrap stable callbacks in `useCallback` when passed to memoized children.
- Use `React.memo` for components that receive the same props frequently (e.g., list items).
- Avoid defining objects/arrays inline in JSX props — they create new references on every render.
- Use dynamic `import()` + `React.lazy` / Next.js `dynamic()` for large components not needed on initial render.

## Data Fetching (Next.js App Router)
- Prefer async server components for data fetching — avoids waterfalls and reduces client JS.
- Use `apiClient` (from `frontend/lib/api-client.ts`) for all backend calls in client components. Never use raw `fetch()` with `credentials: "include"`.
- Handle loading and error states explicitly. Never silently swallow fetch errors.

## TypeScript
- All component props must be typed with explicit interfaces (not inline types in JSX).
- Avoid `any`. Use `unknown` and narrow with type guards.
- Use Zod + React Hook Form for all form validation.

## Ledgerly-Specific Rules
- Always use `apiClient.get/post/delete()` for API calls — it injects `Authorization: Bearer {token}` automatically.
- Enum values sent to the backend must exactly match the backend enum strings (e.g., category values are lowercase: `"shopping"`, not `"SHOPPING"`).
- Financial amounts displayed must use `Decimal` or format via utility — never `Number.toFixed()` for rounding.
