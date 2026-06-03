<!-- last_verified: 2026-06-03 -->
# Feature: Avatar-Video Render Job

## Purpose
Drive a single take from request to archived MP4: ask the provider to render, poll until
it's done, download the result MP4, and store it in B2 — updating the manifest at every step.

## Used By
- API: `POST /projects` and `POST /projects/{id}/takes` (both schedule the job)
- Job: FastAPI `BackgroundTasks` worker `run_render(project_id, take_id)`

## Core Functions
- `services/api/app/service/render.py` — `create_project()`, `render_take()`, `run_render()`, `_poll_to_completion()`
- `services/api/app/repo/avatar_video/` — `create_render()`, `poll_render()` (provider adapter)
- `services/api/app/repo/projects_store.py` — `put_bytes()`, `read_object()`, `download_remote()`
- `services/api/app/service/metadata.py` — `extract_video_duration()`

## Canonical Files
- Render orchestration: `services/api/app/service/render.py`

## Inputs
- A persisted project (manifest, `script.txt`, optional `avatar.<ext>`) and a take id

## Outputs
- A stored MP4 at `avatar-projects/<id>/takes/<take_id>.mp4`
- A rewritten `project.json` with the take's status, `video_key`, and `duration_seconds`
- Side effects: one provider create call, N provider poll calls, one HTTP download, B2 writes

## Flow
1. `create_project()` persists `script.txt` (+ uploaded avatar) and an initial manifest with
   one PENDING take, then returns `202`. The router schedules `run_render`.
2. `run_render()` marks the take/project RENDERING and saves the manifest.
3. The provider's `create_render()` submits the job (stock presenter id or uploaded image +
   the script + voice) and returns a job id, which is saved to the manifest.
4. `_poll_to_completion()` calls `poll_render()` every `AVATAR_POLL_INTERVAL_SECONDS` until
   the job reports done (or `AVATAR_POLL_TIMEOUT_SECONDS` elapses → `TimeoutError`).
5. On done, `download_remote()` GETs the result MP4 (plain `httpx`, capped size), `put_bytes()`
   writes it to `takes/<take_id>.mp4`, duration is extracted, and the manifest is marked COMPLETE.
6. `render_take()` appends a new PENDING take to iterate; the same worker renders it.

## Edge Cases
- Provider create/poll error → take + project marked FAILED with the error on the manifest
- Poll timeout → `TimeoutError` → FAILED (manifest preserved; the user can render another take)
- Oversized result → download is capped (`_MAX_RENDER_BYTES`) → FAILED
- Server restart mid-render → the in-process task is lost, but the durable manifest keeps the
  take PENDING/RENDERING; rendering another take recovers the project (see RELIABILITY.md)

## UX States (driven by manifest status, polled by the Library)
- pending / rendering: in-flight banner + spinning status badge
- complete: take is playable inline and downloadable
- failed: the error is surfaced; "render another take" stays available

## Verification
- Test files: `services/api/tests/test_render.py` (fake in-memory provider fixture in `conftest.py`)
- Required cases: download+archive happy path, iteration (second take), provider failure
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Out of scope (v1)
- Multi-scene composition / ffmpeg concat (single take only)
- Provider webhooks (we poll instead)

## Related Docs
- [New Avatar Video studio](create-studio.md)
- [Pluggable avatar providers](avatar-providers.md)
- [RELIABILITY.md](../RELIABILITY.md)
