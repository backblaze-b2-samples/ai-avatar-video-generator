<!-- last_verified: 2026-06-03 -->
# Feature: Scoped Library

## Purpose
Browse, play, iterate on, and delete avatar-video projects — scoped to the
`avatar-projects/` prefix (the sample-specific complement to the full-bucket File Explorer).

## Used By
- UI: `/library` page
- API: `GET /projects`, `GET /projects/{id}`, `POST /projects/{id}/takes`,
  `GET /projects/{id}/takes/{take_id}/video`, `DELETE /projects/{id}`

## Core Functions
- `apps/web/src/components/library/project-grid.tsx` — project cards (status, take count, duration)
- `apps/web/src/components/library/project-detail.tsx` — detail header, render-another-take, delete
- `apps/web/src/components/library/take-player.tsx` — inline `<video controls>` + take history
- `apps/web/src/components/library/status-badge.tsx` — render status badge
- `apps/web/src/lib/queries.ts` — `useProjects()`, `useProject()`, `useRenderAnotherTake()`, `useDeleteProject()`
- `services/api/app/service/projects.py` — `list_projects()`, `get_project()`, `take_stream_url()`, `take_download_url()`, `delete_project()`

## Canonical Files
- Library detail: `apps/web/src/components/library/project-detail.tsx`
- Scoped listing logic: `services/api/app/service/projects.py`

## Inputs
- Optional `?project=<id>` query param to deep-link a project
- User selection of a project / take

## Outputs
- `GET /projects` → `ProjectSummary[]` (scoped to `avatar-projects/`, newest first)
- `GET /projects/{id}` → `ProjectDetail` (takes with status + duration)
- `GET /projects/{id}/takes/{take}/video?download=false` → `{ url }` presigned inline GET (streaming)
- `GET /projects/{id}/takes/{take}/video?download=true` → `{ url }` presigned attachment GET
- `POST /projects/{id}/takes` → `202` + updated `ProjectDetail` (new pending take)
- `DELETE /projects/{id}` → deletes every object under the project prefix

## Flow
- The grid lists projects from the scoped prefix; while any is rendering it polls every 3s
- Selecting a project opens the detail with a `<video>` player; the newest completed take
  auto-loads via a presigned inline B2 URL (browser issues Range reads against B2)
- The take history lists every take with status + duration; play or download any of them
- "Render another take" appends a pending take and re-renders the same script + avatar
- Delete removes the whole project folder from B2 after a confirm dialog

## Edge Cases
- Take not finished → its play/download buttons are disabled; status badge shows progress
- Project not found / bad id → 404 / 400 with an inline ErrorState
- Provider failure on a take → the detail surfaces the error; other takes still play

## UX States
- Loading: skeleton grid / detail
- Empty: "No avatar videos yet"
- In-flight: rendering banner + spinning badge (auto-refreshes)
- Error: inline ErrorState with Retry

## Verification
- Test files: `services/api/tests/test_projects.py`
- Required cases: scoped listing, detail derived fields, key validation
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [New Avatar Video studio](create-studio.md)
- [Render job](render.md)
- [File Browser](file-browser.md) (the kept full-bucket explorer)
