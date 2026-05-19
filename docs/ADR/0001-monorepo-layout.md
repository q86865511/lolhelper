# ADR 0001 — Monorepo layout (pnpm + Turborepo + standalone Python)

**Date**: 2026-05-18
**Status**: Accepted

## Context

Three deliverables (`backend`, `frontend`, `client`) plus shared TypeScript
types. Need a layout that supports:
- Independent dev/build cycles per package
- A shared TypeScript types package consumed by frontend and Electron client
- Python backend's own dependency manager (Poetry / uv) independent of pnpm

## Decision

Single Git repo, pnpm workspaces, with the Python backend a sibling that
**doesn't** participate in pnpm/turbo.

```
/
├── backend/         (uv-managed Python)
├── frontend/        (Next.js, pnpm workspace)
├── client/          (Electron, pnpm workspace)
├── packages/
│   └── shared-types/ (TS-only, pnpm workspace)
├── infra/           (docker-compose, ops scripts)
└── docs/
```

Turborepo orchestrates JS/TS builds (frontend, client, shared-types).
`backend` builds and runs via `uv` directly; root `package.json` exposes
`pnpm backend:dev` / `pnpm backend:migrate` for convenience.

## Alternatives considered

- **Nx**: more powerful but heavier; we don't need its code generators
- **Multiple repos**: shared types become a versioning headache early
- **Bazel**: gigantic overkill for 3 packages
- **Python in pnpm**: would require a Python-aware tool that doesn't exist
  in JS land

## Consequences

- ✅ One `git clone` gets everything
- ✅ TS types stay in sync between frontend + client
- ⚠️ Devs need both pnpm and uv installed
- ⚠️ CI matrix has two language toolchains
