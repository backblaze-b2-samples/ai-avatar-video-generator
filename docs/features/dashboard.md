<!-- last_verified: 2026-06-03 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of avatar-video activity: how many projects exist, how many
takes have been rendered, total minutes of video, storage used, and recent renders.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /projects/stats`, `GET /projects/stats/activity`, `GET /projects`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (projects, renders, minutes, storage)
- `apps/web/src/components/dashboard/renders-chart.tsx` — bar chart of completed renders per day
- `apps/web/src/components/dashboard/recent-renders-table.tsx` — most recent projects
- `apps/web/src/lib/queries.ts` — `useProjectStats()`, `useProjectActivity()`, `useProjects()`
- `services/api/app/runtime/projects.py` — `GET /projects/stats` + `/activity` handlers
- `services/api/app/service/projects.py` — `project_stats()`, `project_activity()`

## Canonical Files
- Dashboard cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Stats service logic: `services/api/app/service/projects.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /projects/stats` → `ProjectStats` (total_projects, total_renders, total_duration_seconds/human, total_size_bytes/human)
- `GET /projects/stats/activity?days=7` → `DailyRendersCount[]` (completed renders per day, server-aggregated)
- `GET /projects` → `ProjectSummary[]` for the recent-renders table (newest first)

## Flow
- Page loads → three parallel API calls (stats, activity, recent projects)
- Stat cards display total projects, total takes rendered, minutes rendered, storage used
- Renders chart shows completed renders/day over the last 7 days
- Recent renders table shows the latest projects with takes, duration, status, created date
- While any project is rendering, the project list polls every 3s so counts update live

## Edge Cases
- API unavailable → stat cards surface an inline ErrorState with Retry (no fake zeros)
- No projects yet → empty chart + empty table messages
- Large project count → stats paginate through all objects using `ContinuationToken`

## UX States
- Loading: skeleton placeholders for cards and table
- Empty: "No avatar videos yet" / "No renders yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_projects.py`
- Required cases: stats with projects, derived counts, list ordering
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
