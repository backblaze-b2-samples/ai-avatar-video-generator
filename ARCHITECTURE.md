<!-- last_verified: 2026-03-10 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - New Avatar Video studio (`/create`): script + avatar + voice -> render
  - Scoped Library (`/library`): per-project archive with inline `<video>` playback and take history
  - Dashboard with avatar-video metrics (projects, renders, minutes, storage) + renders-per-day chart
  - Full-bucket File browser + generic Upload (kept B2 scaffolding)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for projects, takes, avatars, voices, plus kept file upload/listing/deletion
  - B2 S3 integration via boto3 (contained to `repo/b2_client.py`)
  - Avatar-video render job: provider create -> poll -> download MP4 -> archive to B2 -> rewrite manifest
  - Provider-agnostic adapter (`repo/avatar_video/`): D-ID default, FAL alternate
  - Take metadata extraction (video duration from the MP4 header, no ffmpeg)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (`Project`, `Take`, `Avatar`, `Voice`, ...)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (projects.py, files, upload, stats, formatting)
    config/                Settings loaded from environment (B2 + avatar provider config)
    repo/                  Data access
      b2_client.py           B2 S3 client (the ONLY boto3 module)
      projects_store.py      B2 access for the domain + provider MP4 download (httpx)
      avatar_video/          Provider adapter: base + did_provider (default) + fal_provider
    service/               Business logic
      render.py              Render job (create -> poll -> download -> archive)
      projects.py            Project manifest CRUD, key/prefix ownership
      metadata.py            Video duration (MP4 header) + checksums
      upload.py, files.py    Kept file scaffolding
    runtime/               FastAPI route handlers (projects.py, files, upload, health, metrics)
  tests/                   pytest tests (structural + integration + projects/render)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. All file keys validated against prefix allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). **The sole datastore — no
  application database.**
  - Each project is a folder under `avatar-projects/<id>/` containing `project.json`
    (the manifest / record of truth), `script.txt`, an optional uploaded `avatar.<ext>`,
    and `takes/<take_id>.mp4` for every render.
  - The Library is scoped to the `avatar-projects/` prefix; the kept File Explorer browses
    the whole bucket. Listing/metadata via `list_objects_v2` (with `Delimiter='/'` to
    enumerate project folders) and `head_object`.
  - Generic uploads land under `uploads/`.

## External Services

- **Backblaze B2 S3 API** — object storage, retrieval, deletion, presigned URLs (the sole datastore)
- **Avatar-video provider** — D-ID by default (`repo/avatar_video/did_provider.py`), FAL
  as an alternate (`fal_provider.py`), selected by `AVATAR_PROVIDER`. The render job
  submits a job, polls for completion, then downloads the result MP4 over plain HTTP
  (`httpx` in `repo/projects_store.py` — not an S3 op, no boto3) and writes it to B2.
  Provider API keys are server-side only.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **API -> avatar provider** — authenticated via a server-side key (D-ID/FAL); keys never reach the client
- **Client -> B2** — presigned GET URLs (short expiry): inline disposition for `<video>` streaming, forced attachment for downloads

## Data Flows

- **Create + render**: Browser -> `POST /projects` (multipart: script + stock-avatar-id
  **or** uploaded avatar) -> `service/render.create_project` writes `script.txt`
  (+ avatar) and the initial `project.json` with one pending take, returns `202` ->
  FastAPI BackgroundTasks runs `run_render`: provider `create_render` -> poll loop until
  done -> download the result MP4 (`httpx` GET) -> `put_object` to `takes/<take_id>.mp4`
  -> extract duration -> rewrite manifest. The client polls `GET /projects/{id}`.
- **Iterate**: Browser -> `POST /projects/{id}/takes` -> appends a new pending take ->
  same background render -> a second MP4 lands under `takes/`.
- **Library list**: Browser -> `GET /projects` -> service lists the `avatar-projects/`
  prefix and reads each manifest -> scoped summaries.
- **Play / download a take**: Browser -> `GET /projects/{id}/takes/{take}/video` -> repo
  generates a presigned GET URL (inline for `<video>` streaming, attachment for download)
  -> browser streams/downloads from B2.
- **Delete**: Browser -> `DELETE /projects/{id}` -> service validates id -> repo deletes
  every object under the project prefix.
- **Kept file scaffolding**: `POST /upload`, `GET /files`, `GET /files/{key}/download`,
  `DELETE /files/{key}` behave as in the starter (full-bucket).

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Render job: `services/api/app/service/render.py`
- Manifest CRUD: `services/api/app/service/projects.py`
- Provider adapter: `services/api/app/repo/avatar_video/` (`base.py`, `did_provider.py`, `fal_provider.py`)
- Domain B2 access + provider download: `services/api/app/repo/projects_store.py`
- B2 S3 client (the only boto3 module): `services/api/app/repo/b2_client.py`
- Project router: `services/api/app/runtime/projects.py`
- Pydantic models: `services/api/app/types/projects.py` (+ `files.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Domain tests: `services/api/tests/test_projects.py`, `services/api/tests/test_render.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [New Avatar Video studio](docs/features/create-studio.md)
- [Avatar-video render job](docs/features/render.md)
- [Scoped Library](docs/features/library.md)
- [Pluggable avatar providers](docs/features/avatar-providers.md)
- [Take metadata](docs/features/metadata-extraction.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md) (kept scaffolding)
- [File Browser](docs/features/file-browser.md) (kept scaffolding)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
