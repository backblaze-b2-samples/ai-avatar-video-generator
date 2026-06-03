<!-- last_verified: 2026-05-01 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/create/    New Avatar Video studio (script + avatar + voice -> render)
  src/app/library/   Scoped avatar-video explorer + inline <video> player
  src/components/studio/   Create form, avatar picker, voice picker
  src/components/library/  Project grid, detail, take player, status badge
  src/components/dashboard/  Avatar-video + render metrics
  src/components/files/    Full-bucket File Explorer (kept B2 scaffolding)
  src/components/upload/   Generic upload (kept B2 scaffolding)
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/avatar_video/  Provider-agnostic adapter (did default, fal alt)
  app/repo/projects_store.py  B2 access for the domain + provider MP4 download (httpx)
  app/service/         render (job), projects (manifest CRUD)
  app/runtime/projects.py  Project + avatar + voice routes
packages/shared/   Shared TypeScript types (mirror the Pydantic models)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

## 2. App Structure

This **is** the AI Avatar Video Generator (forked from `vibe-coding-starter-kit`). The
pieces below are where the app's behavior lives, plus the B2 scaffolding kept from the
starter.

**App surfaces (the avatar-video feature set)**
- **New Avatar Video studio** — `/create`, `apps/web/src/app/create/` +
  `apps/web/src/components/studio/`. Type/upload a script, pick a stock avatar or upload a
  custom photo/clip, pick a voice, `POST /projects` (multipart) to start a render.
- **Library** — `/library`, `apps/web/src/app/library/` +
  `apps/web/src/components/library/`. Scoped explorer of `avatar-projects/`, an inline
  `<video controls>` player streaming takes from presigned B2 URLs, take/iteration
  history, "render another take", download, and delete.
- **Dashboard** — `/`, `apps/web/src/components/dashboard/`. Avatar-video metrics (total
  projects, total renders/takes, minutes rendered, storage used), a renders-per-day
  chart, and recent renders.
- **Backend** — the render job in `service/render.py` (provider create -> poll -> download
  MP4 -> put to B2 -> rewrite manifest), manifest CRUD in `service/projects.py`, the
  provider adapter in `repo/avatar_video/`, and B2 + provider-download access in
  `repo/projects_store.py`. The project router is `runtime/projects.py`. **B2 is the sole
  datastore** — `project.json` per project; there is no database.

**Kept B2 scaffolding (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the
  design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build
  new screens with these primitives; never edit the generated `components/ui/` files
  directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and
  `apps/web/src/components/files/` — full-bucket browse. The Files sidebar entry stays.
- **Upload.** `/upload` route + `apps/web/src/components/upload/` — generic drag-and-drop
  upload to `uploads/`. The Upload sidebar entry stays.
- The sidebar nav (Dashboard, New Avatar Video, Library, Upload, Files, Settings, plus the
  Design System utility link).

**Why the scaffolding stays**
- The UI kit, Files, and Upload pages are the reusable B2-backed surface inherited from the
  starter. New aggregations and screens must flow through the same `runtime -> service ->
  repo` layering and be exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` —
  no bare `useEffect + fetch`. Update `docs/features/<feature>.md` in the same PR as any
  feature change (see §9).

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/` — in this app it is contained entirely to
  `repo/b2_client.py`. (The provider result-MP4 download is a plain HTTP GET with
  `httpx` in `repo/projects_store.py`; that is allowed — it is not an S3 op and never
  touches boto3.)
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters (avatar providers live in
  `repo/avatar_video/`; their SDK/HTTP clients are lazy-built so only the active provider
  is required)
- Provider API keys are read server-side from settings only — never returned to the client
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| New Avatar Video studio | [docs/features/create-studio.md](docs/features/create-studio.md) |
| Avatar-video render job | [docs/features/render.md](docs/features/render.md) |
| Scoped Library + video player | [docs/features/library.md](docs/features/library.md) |
| Pluggable avatar providers | [docs/features/avatar-providers.md](docs/features/avatar-providers.md) |
| Take metadata (duration + checksum) | [docs/features/metadata-extraction.md](docs/features/metadata-extraction.md) |
| Dashboard metrics | [docs/features/dashboard.md](docs/features/dashboard.md) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
