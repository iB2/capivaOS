# Blueprint Reference: Next.js TypeScript (Node.js 22 / Next.js / App Router)

> This file is the bridge between the stack-agnostic harness and the Next.js TypeScript blueprint.
> Agent roles and skills read this file to get stack-specific patterns, commands, and standards.

## §project — Blueprint Project

- **Path**: *(set per project — e.g., `C:\Users\bruno\Documents\DevProjects\my-nextjs-app\`)*
- **Type**: Next.js full-stack application with App Router
- **Contents**: App routes, components, lib, API routes, tests, Dockerfile, CI pipeline
- **Status**: Production-ready scaffold

---

## §stack — Technology Identity

| Property | Value |
|----------|-------|
| Language | TypeScript 5.x (strict mode) |
| Runtime | Node.js 22 LTS |
| Module system | ESM (`"type": "module"`) |
| Framework | Next.js 15+ (App Router) |
| UI library | React 19 |
| Styling | Tailwind CSS v4 (via `@tailwindcss/postcss` or `@tailwindcss/vite`) |
| Component library | shadcn/ui (Radix UI primitives + CVA + clsx + tailwind-merge) |
| Icons | Lucide React |
| Data fetching | TanStack React Query 5.x (client), Server Components (server) |
| Forms | React Hook Form 7.x + Zod 3.x |
| State management | Zustand 5.x (when needed — prefer server state via React Query) |
| Toasts | Sonner |
| Animation | Framer Motion 12.x (when needed) |
| Logging | Pino (structured JSON logging) |
| Cache | Redis (ioredis) — when server-side caching is needed |
| Queue | BullMQ (when async job processing is needed) |
| Package manager | npm |

---

## §architecture — Project Structure

```
src/
  app/
    layout.tsx                 # Root layout (providers, fonts, metadata)
    page.tsx                   # Home page
    [feature]/                 # Feature route segments
      page.tsx                 # Page component (Server Component by default)
      loading.tsx              # Loading UI (Suspense boundary)
      error.tsx                # Error boundary
    api/
      [endpoint]/
        route.ts               # API route handler (GET, POST, etc.)
  components/
    ui/                        # shadcn/ui primitives (Button, Dialog, etc.)
    [feature]/                 # Feature-specific components
  lib/
    utils.ts                   # Shared utilities (cn() helper, etc.)
    [domain].ts                # Domain logic modules
  hooks/
    use-[name].ts              # Custom React hooks
  types/
    index.ts                   # Shared TypeScript types
  middleware.ts                # Next.js middleware (auth, redirects)
```

### Architecture Rules (INVIOLABLE)

1. **Server Components by default.** Only add `"use client"` when the component needs browser APIs, event handlers, or React hooks.
2. **No business logic in route handlers.** API routes are thin — validate input (Zod), call a service function from `lib/`, return the response.
3. **No prop drilling.** Use React Context, Zustand, or URL search params for cross-component state.
4. **Colocation.** Feature-specific components live next to their route segment, not in a global `components/` folder. Shared components go in `components/`.
5. **Path alias.** `@/*` maps to `./src/*` (configured in `tsconfig.json`).

### Dependency Direction

```
Route Segments (app/) → Components → Hooks → Lib (domain logic) → Types
```

- **Components** never import from `app/` (no circular deps)
- **Lib** modules are pure functions — no React, no hooks, no components
- **Hooks** can import from `lib/` but not from `components/`

### Namespace Convention

Feature-based organization. Each route segment is self-contained:

```
app/
  dashboard/
    page.tsx           # Server Component — fetches data
    DashboardClient.tsx  # Client Component — interactive UI
    actions.ts         # Server Actions (if needed)
```

---

## §coding-standards — Naming Conventions & Code Style

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Component files | PascalCase | `UserProfile.tsx` |
| Non-component files | kebab-case | `use-auth.ts`, `api-client.ts` |
| Route segments | kebab-case | `app/user-profile/page.tsx` |
| Components | PascalCase | `export function UserProfile()` |
| Hooks | camelCase with `use` prefix | `export function useAuth()` |
| Utility functions | camelCase | `export function formatDate()` |
| Constants | UPPER_SNAKE_CASE | `const MAX_RETRIES = 3` |
| Types/Interfaces | PascalCase | `type UserProfile = { ... }` |
| Env vars (public) | `NEXT_PUBLIC_` prefix | `NEXT_PUBLIC_API_URL` |
| Env vars (server) | UPPER_SNAKE_CASE | `DATABASE_URL` |
| CSS variables | kebab-case | `--color-primary` |

### TypeScript Rules

- **Strict mode enabled.** `strict: true` in `tsconfig.json`.
- **No `any`.** Use `unknown` + type narrowing. `noImplicitAny: true`.
- **Prefer `type` over `interface`** unless extending or declaration merging is needed.
- **Use `satisfies`** for type checking without widening: `const config = { ... } satisfies Config`.
- **No non-null assertions (`!`).** Handle null/undefined explicitly.
- **No type assertions (`as`)** unless narrowing from `unknown` after validation.

### React Patterns

- **Function declarations** for components: `export function Card() {}`, not `const Card = () => {}`.
- **Props as destructured params**: `function Card({ title, children }: CardProps)`.
- **No default exports** for components (named exports only). Exception: `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx` (Next.js convention requires default exports).
- **`"use client"` only when needed.** Server Components are the default.
- **Server Actions** for mutations when possible (form submissions, data writes).
- **Avoid `useEffect` for data fetching.** Use Server Components or React Query.

### Tailwind & Styling

- **`cn()` helper** from `lib/utils.ts` for conditional classes: `cn("base-class", condition && "conditional-class")`.
- **No inline styles.** All styling via Tailwind utilities or CSS variables.
- **shadcn/ui components** are copied into the project (not imported from a package). Customize freely.
- **CSS variables for theming** via `app/globals.css`:
  ```css
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    /* ... */
  }
  ```

### Import Order

1. React / Next.js imports
2. Third-party library imports
3. Internal imports (`@/` alias)
4. Relative imports
5. Type-only imports (`import type { ... }`)

### Error Handling

- **API routes**: Return `NextResponse.json({ error: "message" }, { status: 4xx })`. No stack traces in responses.
- **Server Components**: Use `error.tsx` boundaries. Log server-side, show user-friendly messages.
- **Client Components**: Use React Error Boundaries or try/catch in event handlers.
- **Form validation**: Zod schemas with React Hook Form `zodResolver`. Validate on client AND server.

### SDLC Code Review Standards

1. **Single responsibility** — one concern per function/component
2. **Function parameters**: 0 ideal, 1-2 normal, 3+ needs a params object
3. **Component props**: destructure at function signature, max 5 direct props before extracting a sub-component
4. **No magic values** — named constants only
5. **Max 2 levels of nesting** per function (extract early returns or helper functions)
6. **No `any`** — reviewer blocks the PR if `any` is used outside test files

### Comments

- No comments explaining WHAT — code and types are self-documenting.
- Comments for WHY only: non-obvious decisions, workarounds, business rules.
- No TODO/HACK without a board task.

---

## §enterprise-patterns — Core Patterns

### Data Fetching (Server Components)

```tsx
// app/users/page.tsx — Server Component (default)
import { getUsers } from "@/lib/users"

export default async function UsersPage() {
  const users = await getUsers()
  return <UserList users={users} />
}
```

### Data Fetching (Client Components)

```tsx
"use client"
import { useQuery } from "@tanstack/react-query"

export function UserSearch() {
  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => fetch("/api/users").then(r => r.json()),
  })
  // ...
}
```

### API Routes

```ts
// app/api/users/route.ts
import { NextResponse } from "next/server"
import { z } from "zod"
import { createUser } from "@/lib/users"

const CreateUserSchema = z.object({
  name: z.string().min(1).max(200),
  email: z.string().email(),
})

export async function POST(request: Request) {
  const body = await request.json()
  const parsed = CreateUserSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 })
  }
  const user = await createUser(parsed.data)
  return NextResponse.json(user, { status: 201 })
}
```

### Form Handling

```tsx
"use client"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email"),
})

type FormData = z.infer<typeof schema>

export function UserForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })
  // ...
}
```

### Soft Deletes

When applicable, entities use a `deletedAt` timestamp — NEVER hard delete:

```ts
// In Prisma schema
model User {
  id        String    @id @default(cuid())
  deletedAt DateTime?
  // ...
}

// In queries — always filter
const users = await prisma.user.findMany({
  where: { deletedAt: null },
})
```

**Deviation allowed**: Status-based lifecycle may replace soft deletes — document via Deviation Record.

### Environment Configuration

```ts
// lib/env.ts — Zod-validated environment
import { z } from "zod"

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  NEXT_PUBLIC_API_URL: z.string().url(),
  // ...
})

export const env = envSchema.parse(process.env)
```

### Middleware (Auth Example)

```ts
// middleware.ts
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const token = request.cookies.get("session")
  if (!token && request.nextUrl.pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/login", request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ["/dashboard/:path*"],
}
```

### Result Pattern

Service functions in `lib/` return a discriminated union instead of throwing for expected failures:

```ts
// lib/result.ts
export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: string }

export function ok<T>(data: T): Result<T> {
  return { ok: true, data }
}

export function fail<T>(error: string): Result<T> {
  return { ok: false, error }
}
```

Usage in service functions:

```ts
// lib/users.ts
import { ok, fail, type Result } from "@/lib/result"

export async function getUserById(id: string): Promise<Result<User>> {
  const user = await prisma.user.findUnique({ where: { id, deletedAt: null } })
  if (!user) return fail("User not found")
  return ok(user)
}
```

- Use `Result<T>` for operations with expected failure modes (not found, validation, business rules)
- Throw only for unexpected errors (network failures, bugs)
- API routes convert `Result` to HTTP responses: `ok` → 200, `fail` → 4xx

### Transport Abstractions

Abstract cache and messaging behind typed wrappers so implementations can be swapped:

```ts
// lib/cache.ts
import { Redis } from "ioredis"

const redis = new Redis(process.env.REDIS_URL)

export async function cacheGet<T>(key: string): Promise<T | null> {
  const raw = await redis.get(key)
  return raw ? (JSON.parse(raw) as T) : null
}

export async function cacheSet<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
  const serialized = JSON.stringify(value)
  if (ttlSeconds) {
    await redis.set(key, serialized, "EX", ttlSeconds)
  } else {
    await redis.set(key, serialized)
  }
}
```

```ts
// lib/queue.ts (when async processing is needed)
import { Queue, Worker } from "bullmq"

export const emailQueue = new Queue("email", { connection: { url: process.env.REDIS_URL } })

// Worker — separate process or API route
new Worker("email", async (job) => {
  await sendEmail(job.data.to, job.data.subject, job.data.body)
}, { connection: { url: process.env.REDIS_URL } })
```

- Cache and queue are optional — add only when the project needs them
- Always abstract behind `lib/` functions, never use Redis/BullMQ directly in components or route handlers

### Structured Logging (Pino)

```ts
// lib/logger.ts
import pino from "pino"

export const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  transport: process.env.NODE_ENV === "development"
    ? { target: "pino-pretty", options: { colorize: true } }
    : undefined,
})
```

Usage:

```ts
import { logger } from "@/lib/logger"

export async function createUser(data: CreateUserInput): Promise<Result<User>> {
  const user = await prisma.user.create({ data })
  logger.info({ userId: user.id }, "user_created")
  return ok(user)
}
```

- **Never use `console.log`** in production code — use `logger.info/warn/error`
- Log structured data (objects), not string interpolation
- Include context keys (userId, action) for searchability
- Development: `pino-pretty` for human-readable output
- Production: JSON output for log aggregation (Datadog, CloudWatch, etc.)

---

## §test-stack — Testing

### Test Stack

| Package | Purpose |
|---------|---------|
| Vitest | Test framework + mocking (vi.fn(), vi.mock()) |
| @testing-library/react | Component rendering + queries |
| @testing-library/user-event | User interaction simulation |
| @testing-library/jest-dom | DOM assertion matchers |
| jsdom | Browser environment for component tests |
| Playwright | E2E testing (browser automation) |
| @vitest/coverage-v8 | Code coverage |

### Test Commands

```bash
npm run test              # vitest --run (unit + integration)
npm run test:watch        # vitest (watch mode)
npm run test:coverage     # vitest run --coverage
npm run test:e2e          # playwright test
npm run test:e2e:ui       # playwright test --ui (interactive)
```

### Coverage Targets

| Scope | Minimum | Target |
|-------|---------|--------|
| Business logic (lib/, services/) | 80% | 90% |
| Components (interactive/complex) | 60% | 75% |
| Overall | 75% | 85% |

### Coverage Exclusions

- `app/layout.tsx`, `app/page.tsx` (thin wrappers)
- shadcn/ui components in `components/ui/` (third-party code)
- Type definitions (`types/`)
- Configuration files

### Test Conventions

- **AAA pattern**: Arrange-Act-Assert with blank line separation
- **Naming**: `describe("ComponentName") > it("should do something when condition")`
- **Organization**: Test file next to source file (`UserProfile.tsx` → `UserProfile.test.tsx`) or in `__tests__/` directory
- **Mocking**: Vitest `vi.mock()` for modules, `vi.fn()` for functions. Never mock what you don't own.
- **Component tests**: Render → interact → assert on DOM output. Test behavior, not implementation.
- **Server Component tests**: Test the underlying `lib/` functions directly (Server Components can't be rendered in jsdom).

### E2E Tests (Playwright)

```ts
// e2e/auth.spec.ts
import { test, expect } from "@playwright/test"

test("user can log in", async ({ page }) => {
  await page.goto("/login")
  await page.fill('[name="email"]', "user@example.com")
  await page.fill('[name="password"]', "password123")
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL("/dashboard")
})
```

Configuration: Chromium only, sequential workers for CI, auto-start dev server, 60s timeout.

### TDD Enforcement

1. **RED**: Write a failing test first
2. **GREEN**: Minimum code to pass
3. **REFACTOR**: Clean up, all tests still green

---

## §static-analysis — Linters & Quality Gates

### Required Tools

| Tool | Purpose | Config File |
|------|---------|-------------|
| ESLint 9 | Linting (flat config) | `eslint.config.mjs` |
| TypeScript (`tsc`) | Type checking | `tsconfig.json` |

### ESLint Configuration

```js
// eslint.config.mjs
import { dirname } from "path"
import { fileURLToPath } from "url"
import { FlatCompat } from "@eslint/eslintrc"

const __dirname = dirname(fileURLToPath(import.meta.url))
const compat = new FlatCompat({ baseDirectory: __dirname })

export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
]
```

### TypeScript Strict Settings

```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true
  }
}
```

### Quality Gate Checks

Before merging, ALL must pass:
1. `npm run lint` — zero ESLint errors
2. `npm run typecheck` (`tsc --noEmit`) — zero type errors
3. `npm run test` — all unit tests green
4. `npm run test:e2e` — all E2E tests green (in CI)
5. `npm run build` — production build succeeds

### Accepted Suppressions

| Rule | When Acceptable |
|------|----------------|
| `@typescript-eslint/no-explicit-any` | External API responses with unknown shape (use `unknown` instead when possible) |
| `@next/next/no-img-element` | When `<Image>` optimization is not applicable (SVGs, external URLs without loader) |
| `react-hooks/exhaustive-deps` | NEVER suppress — fix the dependency array |

---

## §ci-cd — Pipeline Configuration

### GitHub Actions (Default)

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test -- --coverage
      - run: npx playwright install --with-deps chromium
      - run: npm run test:e2e

  build:
    runs-on: ubuntu-latest
    needs: lint-and-test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npm run build
```

### Azure Pipelines (Enterprise — SSB/client projects)

```yaml
# azure-pipelines.yml
trigger: { branches: { include: [main] } }
pool: { vmImage: ubuntu-latest }

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - task: NodeTool@0
            inputs: { versionSpec: '22.x' }
          - script: npm ci
          - script: npm run lint
          - script: npm run typecheck
          - script: npm run test -- --coverage
          - script: npm run build
  - stage: DeployDev
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    # Deploy to dev environment
  - stage: DeployProd
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    # Manual approval gate + deploy
```

### Environment Progression

```
DEV → Staging/Test → Production
```

- Merge to `main` triggers dev deploy
- Staging requires successful dev deployment
- Production requires manual approval

### Deployment Targets (choose per project)

| Target | When |
|--------|------|
| Vercel | Default for Next.js (zero-config, preview deploys) |
| Docker → Portainer/Swarm | Self-hosted, full control |
| Azure Container Apps | Enterprise/client deployments |
| Azure Static Web Apps | SPA-only (no SSR needed) |

### SDLC Compliance Mapping

| Harness Phase | SDLC Phase |
|---------------|------------|
| Phase 1 (GRILL_SPEC) | SDLC Phase 3 (Requirement Analysis) |
| Phase 2 (PLAN) | SDLC Phase 4 (Solution Design) |
| Phase 3 (IMPLEMENT) | SDLC Phase 6 (Refinement & Development) |
| Phase 4 (TEST_VERIFY) | SDLC Phase 7 (Testing & QA) |
| Phase 5 (FINISH) | SDLC Phases 6-8 (Code Review → CAB → Deploy) |

---

## §qa-checklist — Review Checklist

Before approving a PR:

- [ ] No `any` types (use `unknown` + type narrowing)
- [ ] No `"use client"` on components that don't need it
- [ ] Server Components used for data fetching (no `useEffect` + fetch)
- [ ] Zod validation on all API route inputs
- [ ] Error boundaries in place (`error.tsx` for route segments)
- [ ] Loading states handled (`loading.tsx` or Suspense boundaries)
- [ ] No hardcoded strings — use environment variables or constants
- [ ] No `console.log` left in production code
- [ ] Tailwind classes use `cn()` for conditionals (no string concatenation)
- [ ] shadcn/ui components used for standard UI patterns (no custom implementations of existing primitives)
- [ ] Responsive design tested (mobile + desktop)
- [ ] Accessibility basics: `aria-label` on icon buttons, `alt` on images, semantic HTML
- [ ] `.env.example` updated if new env vars added
- [ ] Tests exist for new business logic in `lib/`
- [ ] E2E tests cover critical user flows

---

## §build-commands — Commands Reference

### Development

```bash
npm run dev               # Next.js dev server (Turbopack)
npm run build             # Production build
npm run start             # Start production server
```

### Quality

```bash
npm run lint              # ESLint
npm run typecheck         # tsc --noEmit
npm run test              # Vitest (unit + integration)
npm run test:coverage     # Vitest with coverage
npm run test:e2e          # Playwright E2E
```

### Database (when using Prisma)

```bash
npx prisma generate       # Generate Prisma client
npx prisma db push        # Push schema to database
npx prisma migrate dev    # Create and apply migration
npx prisma studio         # Open database GUI
```

### Docker

```bash
docker build -t app .                    # Build image
docker run -p 3000:3000 app              # Run container
docker compose up                        # Full stack (app + db + redis)
```

### shadcn/ui

```bash
npx shadcn@latest add button             # Add a component
npx shadcn@latest add dialog card input  # Add multiple components
npx shadcn@latest diff                   # Check for updates
```

---

## §deviation-rules — When to Deviate

### Accepted Deviations (no Deviation Record needed)

- Using `page.tsx` default exports (Next.js convention requires it)
- Relaxing `noUnusedLocals` during active development (must be clean before PR)
- Using `any` for test mocks (only in test files, never in source)

### Deviations Requiring a Deviation Record

- Adding a CSS-in-JS library alongside Tailwind
- Using a state management library other than Zustand
- Skipping E2E tests for a feature
- Using `pages/` router instead of `app/` router
- Disabling TypeScript strict mode for any file
- Adding MUI, Chakra, or another component library alongside shadcn/ui

---

*Blueprint: Next.js TypeScript — Capiva OS Development Harness*
*Stack: Node.js 22 + TypeScript 5.x + Next.js 15+ + App Router + Tailwind CSS + shadcn/ui*
