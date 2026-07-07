# Blueprint: Next.js TypeScript (Node.js 22 + TypeScript 5.x + Next.js 15+)

> Stack reference for Capiva OS harness. See `reference.md` for the full blueprint.

## Stack Summary

- **Runtime**: Node.js 22 LTS
- **Language**: TypeScript 5.x (strict mode)
- **Framework**: Next.js 15+ (App Router)
- **UI**: React 19 + Tailwind CSS v4 + shadcn/ui (Radix primitives)
- **Testing**: Vitest (unit) + Playwright (E2E)
- **Linting**: ESLint 9 (flat config) + TypeScript strict
- **CI/CD**: GitHub Actions (default) or Azure Pipelines (enterprise)
- **Deployment**: Vercel, Docker, Azure Container Apps, or Azure Static Web Apps
