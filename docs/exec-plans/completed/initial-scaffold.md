<!-- last_verified: 2026-06-03 -->
# Initial Scaffold — AI Avatar Video Generator (Phase 5)

Forked from `vibe-coding-starter-kit`. This is the as-built record of the initial scaffold.

## Goal
Turn a script + an avatar into a talking-head video with synced voice, archiving every
render ("take") per project in Backblaze B2. B2 is the sole datastore — a per-project
`project.json` manifest is the record of truth; there is no database. Closest analog: the
sibling `ai-audiobook-generator` (input → provider job → scoped library), mapped 1:1.

## Kept from the starter (B2 scaffolding)
- UI kit / design system (`components/ui/`, `globals.css`, `/design`)
- Full-bucket File Explorer (`/files`) and generic Upload (`/upload`) + sidebar entries
- Settings (`/settings`)
- Layered backend (`types/config/repo/service/runtime`), `repo/b2_client.py`, health/metrics
- Structural tests + kept integration tests (`test_health`, `test_upload_*`, `test_delete`, etc.)

## Added (avatar-video domain)
- **Studio** — `/create` + `components/studio/` (create-form, avatar-picker, voice-picker)
- **Scoped Library** — `/library` + `components/library/` (project-grid, project-detail,
  take-player with inline `<video>`, status-badge), scoped to `avatar-projects/`
- **Dashboard** — avatar-video metrics (projects, renders, minutes, storage) + renders chart
- **Backend** — `types/projects.py`; `repo/avatar_video/` (base + did default + fal alt;
  HeyGen documented extension slot); `repo/projects_store.py` (B2 access + `httpx`
  result-MP4 download); `service/projects.py` (manifest CRUD); `service/render.py` (the
  BackgroundTasks render job: provider create → poll → download → put to B2 → rewrite
  manifest; multiple takes per project); `runtime/projects.py`
- **Tests** — `test_projects.py` (manifest CRUD), `test_render.py` (job flow against a fake
  in-memory provider fixture in `conftest.py`)
- **Config** — `AVATAR_PROVIDER`, `DID_API_KEY`, `FAL_KEY`, `AVATAR_DEFAULT_VOICE`,
  `AVATAR_DEFAULT_AVATAR`, `AVATAR_POLL_INTERVAL_SECONDS`, `AVATAR_POLL_TIMEOUT_SECONDS`

## Trimmed
- Dashboard widgets rewritten from upload-centric to avatar-video metrics
- `service/metadata.py` reduced from image/EXIF/PDF to MP4 video-duration (header parse) + checksum
- Starter exec-plan history cleared; tech-debt tracker reset

## Standards honored
1. S3 API is the default — boto3 only in `repo/b2_client.py`; no native B2 SDK. The provider
   result-MP4 download is a plain HTTP GET (`httpx`) in the repo layer — not an S3 op.
2. Custom user agent on the S3 client —
   `user_agent_extra="ai-avatar-video-generator (backblaze-b2-samples)"`.
3. Standardized B2 env names — `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`,
   `B2_BUCKET_NAME`, `B2_REGION` (+ optional `B2_PUBLIC_URL_BASE`).

## B2 layout
```
avatar-projects/<id>/project.json          manifest (record of truth)
avatar-projects/<id>/script.txt            durable script
avatar-projects/<id>/avatar.<ext>          custom avatar (upload only)
avatar-projects/<id>/takes/<take_id>.mp4   each rendered take
uploads/                                   generic Upload page
```

## Verification at scaffold time
`pnpm lint`, `pnpm build`, `pnpm lint:api`, `pnpm test:api` (35 passed), `pnpm check:structure`
all green; `b2-doctor` clean.

## Out of scope (v1)
Multi-scene composition / ffmpeg concat; custom voice cloning; real-time streaming avatars;
provider webhooks (we poll). All noted as extension points in the docs.


---

## Appendix — Normalized approved plan archive

_Archived from the Phase-1 scratch plan and normalized for current repository
paths and B2 standards. This is not a verbatim historical snapshot._

# Scaffold Plan — `ai-avatar-video-generator`

Forked from **vibe-coding-starter-kit** (cloned fresh into a session-scoped
scratch directory). This plan is the contract for the builder and reviewer
subagents. The closest existing analog is the
sibling **ai-audiobook-generator** (input → provider job → scoped library);
the avatar generator maps onto it almost 1:1.

## Decisions locked with the user
- **Avatar source:** stock **+** custom upload (uploads archived in B2).
- **Scene scope:** single-take, with cheap **iteration** (multiple takes per script). No local compositing.
- **Default provider:** **D-ID** — the one with a real free-trial-through-the-API
  (14-day trial, 20 credits ≈ 5 min video, **no credit card**, watermarked; takes a
  still image/video *or* a stock presenter + a script and returns an MP4 with synced
  voice). **FAL** is the scaffolded alternate adapter ($20 free signup credits,
  pay-per-use lip-sync models). **HeyGen** is documented as a third adapter slot
  (richest catalog, but its API generally needs a paid plan → not the free default).

---

## 1. Purpose

`ai-avatar-video-generator` is a Backblaze B2 sample that turns a **script + an
avatar** into a **talking-head video with synced voice**. A user types or uploads a
script, picks a stock avatar or uploads a custom photo, chooses a voice, and renders
a video; every render ("take") is archived per project so users can iterate (multiple
takes per script) and compare. It's a HeyGen / Synthesia / D-ID-style demo aimed at
developers evaluating B2 for **media-heavy, iterative AI workloads** — each render is
a sizable MP4, and a single project accumulates several. It shows B2 as the **sole
datastore**: scripts, custom avatar references, and rendered videos all live in the
bucket; a per-project `project.json` manifest is the record of truth. No database.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling — strip what this app doesn't need, keep the reusable
B2 scaffolding, add the avatar-video domain. Mapping to the audiobook analog:
`Book→Project`, `Chapter→Take`, `repo/tts/→repo/avatar_video/`,
`service/narration.py→service/render.py`, and **no `audio_master.py`/ffmpeg** (single-take ⇒ no assembler).

### KEEP (as-is — starter contract)
- **UI kit / design system** — `apps/web/src/components/ui/` (shadcn primitives),
  tokens in `apps/web/src/app/globals.css`, the `/design` page + `components/design/`.
  Build new screens with these primitives; never edit generated `components/ui/` files.
- **Full-bucket File Explorer** — `/files` route, `app/files/`, `components/files/`,
  and the Files sidebar entry. *(Non-negotiable keep — full-bucket browse stays.)*
- **Generic Upload** — `/upload` route, `app/upload/`, `components/upload/`, and the
  Upload sidebar entry (drag-and-drop to `uploads/`).
- **Settings** — `/settings` + `components/settings/`.
- **Backend scaffolding** — layered `types/config/repo/service/runtime`;
  `repo/b2_client.py` (S3 client w/ custom user agent), `runtime/health.py`,
  `runtime/metrics.py`, `runtime/files.py`, `runtime/upload.py`, `service/files.py`,
  `service/upload.py`, `service/metadata.py`; structured JSON logging; `/health` + `/metrics`.
- **Structural tests** — `tests/test_structure.py` (layering, no-boto3-outside-repo,
  file-size, all-layers). Plus keep `test_health`, `test_upload_*`, `test_delete`,
  `test_error_handling`.
- **Data layer discipline** — every fetch through TanStack Query hooks in
  `apps/web/src/lib/queries.ts`; new endpoints touch `runtime/*` + `lib/api-client.ts`
  + `lib/queries.ts`.

### TRIM (remove/replace relative to the starter)
- **Dashboard default widgets** — replace the upload-centric stats/chart/recent-uploads
  in `components/dashboard/` with avatar-video metrics (see ADD). The dashboard *surface*
  stays; its content is the one screen meant to be rewritten per app.
- **Image/PDF metadata extraction** — `service/metadata.py` currently does image
  dimensions / EXIF / PDF info. Trim that to a slim **video-duration (+ checksum)**
  extractor for rendered takes. Rewrite `docs/features/metadata-extraction.md` accordingly.
- **Starter exec-plan history** — clear `docs/exec-plans/completed/*` (starter-specific)
  and reset `docs/exec-plans/tech-debt-tracker.md` to an empty tracker. The Phase-5
  scaffold plan lands in `docs/exec-plans/completed/initial-scaffold.md`.
- **Starter-only tests** — drop `test_download_stats`, `test_recent_files`,
  `test_upload_activity` if they assert upload-dashboard behavior that the new dashboard
  replaces (keep whatever still maps to retained endpoints).

### ADD (new for `ai-avatar-video-generator`)

**Sample-specific scoped asset explorer (non-negotiable add):**
- **Library** — `/library` route, `app/library/`, `components/library/`. A view scoped
  to `avatar-projects/` (not the whole bucket): project grid (avatar thumbnail, status
  badge, take count), project detail with an inline `<video controls>` player streaming
  the selected take from a presigned B2 URL, the take/iteration history, "Render another
  take", download, and delete. This is the sample-specific complement to the kept
  full-bucket `/files` explorer.

**Frontend**
- `/create` route + `components/studio/` — **New Avatar Video studio**: script input
  (textarea *or* `.txt` upload toggle), avatar picker (grid from `GET /avatars` stock
  catalog **+** "upload custom photo/clip" dropzone), voice `<select>` (`GET /voices`),
  "Render video" → `POST /projects` → land on the project detail with the in-flight take.
- `components/dashboard/` — avatar-video metrics: total projects, total renders (takes),
  minutes rendered, storage used; a renders-per-day chart; recent renders table.
- Sidebar (`components/layout/`) nav order: **Dashboard · New Avatar Video · Library ·
  Upload · Files · Settings** + the Design System utility link.
- `lib/api-client.ts` + `lib/queries.ts` — project/avatar/voice endpoints + hooks.
- `packages/shared/src/types.ts` — `Project`, `Take`, `Avatar`, `Voice`, request/detail
  types mirroring the Pydantic models.

**Backend (layered, mirrors the audiobook fork)**
- `types/projects.py` — domain models (see §Domain model below).
- `repo/avatar_video/` — provider-agnostic adapter:
  - `base.py` — `AvatarVideoProvider` protocol, `RenderResult`, `AvatarVideoError`,
    `get_provider()` factory keyed on `settings.avatar_provider`.
  - `did_provider.py` — **default**, full skeleton against D-ID's create-talk → poll →
    result-url endpoints (real endpoints referenced; API key from env).
  - `fal_provider.py` — alternate skeleton (lip-sync model; supplies image+audio).
  - HeyGen: documented extension point in `docs/features/avatar-providers.md` (optional stub only).
- `repo/projects_store.py` — B2 access for the domain: `project.json` manifest load/save,
  key helpers, and a small **remote-download helper** (`httpx`/`requests` GET of the
  provider's result URL → bytes). *boto3 stays only in `b2_client.py`*; the HTTP fetch is
  fine in the repo layer.
- Extend `repo/b2_client.py` (or `repo/__init__`) with `put_bytes(data, key, content_type)`
  and `read_object(key) -> bytes | None` (as the audiobook did), reused by the render job.
- `service/projects.py` — manifest CRUD, project creation, key/prefix ownership.
- `service/render.py` — the render job (analog of `narration.py`): `create_project()`
  persists `script.txt` (+ uploaded avatar) and the initial manifest then returns;
  `run_render(project_id, take_id)` is the BackgroundTasks worker — create provider job →
  **poll loop** (interval/timeout from settings) → on done download the MP4 from the
  result URL → `put_bytes` to `takes/<take_id>.mp4` → extract duration → rewrite manifest;
  `render_take()` appends a new pending take for iteration.
- `runtime/projects.py` — router:
  `POST /projects` (multipart: script + stock-avatar-id **or** uploaded avatar; schedules render),
  `GET /projects` (scoped summaries), `GET /projects/{id}`,
  `POST /projects/{id}/takes` (render another take), `DELETE /projects/{id}`,
  `GET /projects/{id}/takes/{take_id}/video` (presigned URL),
  `GET /avatars` (stock catalog), `GET /voices`.

**Tests**
- `tests/test_projects.py` (manifest CRUD), `tests/test_render.py` (job flow against a
  **fake in-memory provider** fixture in `conftest.py`). Keep structural tests green.

**Config / env** — see §Env below.

### B2 storage layout (per-project archive)
```
avatar-projects/<project_id>/project.json          # manifest — record of truth (status, avatar ref, voice, takes[])
avatar-projects/<project_id>/script.txt            # durable script text
avatar-projects/<project_id>/avatar.<ext>          # uploaded custom avatar (only when source = upload)
avatar-projects/<project_id>/takes/<take_id>.mp4   # each rendered take (the iteration story)
uploads/                                            # generic Upload page (kept scaffolding)
```

### Domain model (`types/projects.py`)
- `RenderStatus(StrEnum)` = `PENDING | RENDERING | COMPLETE | FAILED` (no `ASSEMBLING` — single-take).
- `Avatar` = `id, name, thumbnail_url?, source: "stock"|"upload"`.
- `Voice` = `id, name, description?, language?`.
- `AvatarRef` (embedded in Project) = `source: "stock"|"upload", provider_avatar_id?, image_key?`.
- `Take` = `take_id, status, provider, provider_job_id?, video_key?, duration_seconds?, error?, created_at`.
- `Project` (= `project.json`) = `id, title, status, script_source, avatar: AvatarRef,
  voice_id, takes: list[Take], created_at, updated_at, error?` + derived `take_count`,
  `renders_complete`, `total_duration_seconds`.
- `ProjectDetail`, `ProjectSummary`, `CreateProjectRequest`, `ProjectStats`, `DailyRendersCount`.

## 3. B2 surface (S3 operations exercised)
**S3-only — no native B2 APIs** (complies with the default standard). Operations:
- `put_object` — manifest, `script.txt`, uploaded avatar, rendered take MP4 (`put_bytes`).
- `get_object` — read manifest, read avatar bytes for upload-based render, read take bytes.
- `list_objects_v2` — scoped Library listing (`avatar-projects/` prefix), full-bucket
  Files explorer, paginated dashboard stats.
- `head_object` — object metadata / existence checks.
- `generate_presigned_url` (GET) — inline `<video>` streaming + downloads (forced
  attachment, short expiry), avatar thumbnails when no public URL.
- `delete_object` — delete a project's keys.
- `head_bucket` — `/health` connectivity check.

**Native B2 usage:** none. **Non-S3 external HTTP:** downloading the provider's rendered
MP4 from its result URL (`httpx`/`requests` GET) — not an S3 op, lives in the repo layer,
does not touch boto3.

## 4. Key features (README + `docs/features/*` stubs)
- **New Avatar Video studio** (`create-studio.md`) — script (type/upload) + avatar
  (stock pick or custom upload) + voice → one click to render.
- **Avatar-video render job** (`render.md`) — provider create → poll → download → archive
  to B2; multiple takes per script; in-process BackgroundTasks (durable manifest, jobs lost on restart).
- **Scoped Library** (`library.md`) — per-project archive with inline video playback,
  take history, download, delete; scoped to `avatar-projects/`.
- **Pluggable avatar providers** (`avatar-providers.md`) — D-ID default, FAL alternate,
  HeyGen extension slot; env-selected; free-trial notes.
- **Full-bucket File Explorer + Upload** (kept) — `file-browser.md`, `file-upload.md`.
- **Take metadata** (`metadata-extraction.md`, rewritten) — video duration + checksum.

## 5. Doc transforms
| Starter doc | Action |
|---|---|
| `README.md` | Rewrite: hero, feature list, setup, **provider setup (D-ID free trial / FAL)**, env, commands; swap UTM tag. |
| `AGENTS.md` | Rewrite §1 repo map + §2 → "App Structure" (app surfaces + kept B2 scaffolding, audiobook-style); update §10 Doc Map. |
| `CLAUDE.md` | Keep as thin pointer (`@AGENTS.md`). |
| `ARCHITECTURE.md` | Add `avatar_video` repo, `projects_store`, `render` service, `projects` runtime, `types/projects`; new data flows (create→render→poll→download→archive); B2 sole datastore + manifest; external services = D-ID/FAL. |
| `docs/features/dashboard.md` | Rewrite for avatar-video metrics. |
| `docs/features/metadata-extraction.md` | Rewrite: image/EXIF/PDF → video duration + checksum. |
| `docs/features/file-upload.md` | Keep (light context edit). |
| `docs/features/file-browser.md` | Keep (light context edit). |
| `docs/features/_template.md` | Keep. |
| `docs/app-workflows.md` | Rewrite journeys: create → render → iterate → download; browse library; full-bucket files. |
| `docs/dev-workflows.md` | Update slug; add provider env setup; note render e2e needs a key (mock/skip in CI). |
| `docs/SECURITY.md` | Update slug; add provider-key handling (server-side only, never to client), avatar-upload validation, presigned-URL reads. |
| `docs/RELIABILITY.md` | In-process render jobs lost on restart (manifest durable); provider rate limits / poll timeout. |
| `docs/design-system.md` | Keep as-is. |
| **New:** `docs/features/create-studio.md`, `render.md`, `library.md`, `avatar-providers.md` | Stub per the feature list. |
| `docs/exec-plans/completed/*`, `tech-debt-tracker.md` | Clear starter history; reset tracker; scaffold plan → `completed/initial-scaffold.md` (Phase 5). |

## 6. Rename table (`vibe-coding-starter-kit` → `ai-avatar-video-generator`)
| Context | From | To |
|---|---|---|
| Directory / repo name | `vibe-coding-starter-kit` | `ai-avatar-video-generator` |
| Title Case (prose, headings) | `Vibe Coding Starter Kit` | `AI Avatar Video Generator` |
| Root `package.json` `name` | `vibe-coding-starter-kit` | `ai-avatar-video-generator` |
| Web workspace pkg | `@vibe-coding-starter-kit/web` | `@ai-avatar-video-generator/web` |
| Shared workspace pkg | `@vibe-coding-starter-kit/shared` | `@ai-avatar-video-generator/shared` |
| `pnpm --filter` refs in root scripts | `@vibe-coding-starter-kit/web` | `@ai-avatar-video-generator/web` |
| TS import paths (`queries.ts`, `api-client.ts`, `file-tree.ts`, components, `next.config.ts`) | `@vibe-coding-starter-kit/shared` | `@ai-avatar-video-generator/shared` |
| `pnpm-lock.yaml` name field | `vibe-coding-starter-kit` | `ai-avatar-video-generator` (regen or edit) |
| S3 **user agent** (`repo/b2_client.py`) | `user_agent_extra="b2ai-oss-start"` | `user_agent_extra="ai-avatar-video-generator (backblaze-b2-samples)"` |
| **UTM** content tag (README B2 links) | `utm_content=b2ai-oss-start` | `utm_content=b2ai-avatar-video-generator` |
| Image tags / workflow slugs | *(none found in starter beyond pkg names)* | builder to verify `infra/railway/` + `.github/` if present and rename any |
| Python modules | n/a (package stays `app`; new modules use snake_case: `avatar_video`, `projects_store`, `render`, `projects`) | — |

## Standards the build must honor (the "parent CLAUDE.md" three)
*(There is no literal top-level `CLAUDE.md`; these are the B2-sample standards enforced
by the `b2-doctor` skill and the starter's AGENTS.md.)*
1. **S3 API is the default** — boto3 S3 only, contained in `repo/b2_client.py`; no
   native B2 SDK. (This app is 100% S3.)
2. **Custom user agent on every S3 client** —
   `user_agent_extra="ai-avatar-video-generator (backblaze-b2-samples)"`.
3. **Standardized `B2_*` env names** — keep the required B2 set exactly (below).

## Env (`.env.example` + `config/settings.py`)
Keep the required B2 set verbatim (source-of-truth standard — no drift):
```
B2_APPLICATION_KEY_ID=...    B2_APPLICATION_KEY=...    B2_BUCKET_NAME=...
B2_REGION=...                B2_PUBLIC_URL_BASE=        (optional public base)
```
Add avatar-video config:
```
AVATAR_PROVIDER=did                 # selects the adapter (did | fal)
DID_API_KEY=your_did_api_key        # default provider (free trial, no card)
# FAL_KEY=your_fal_key              # alternate provider
AVATAR_DEFAULT_VOICE=               # optional provider voice id
AVATAR_DEFAULT_AVATAR=              # optional stock avatar/presenter id
# AVATAR_POLL_INTERVAL_SECONDS=3    AVATAR_POLL_TIMEOUT_SECONDS=600
```
New `Settings` fields: `avatar_provider`, `did_api_key`, `fal_key`,
`avatar_default_voice`, `avatar_default_avatar`, `avatar_poll_interval_seconds`,
`avatar_poll_timeout_seconds`.

## Out of scope (v1)
Multi-scene composition / ffmpeg concat; custom voice cloning; real-time streaming
avatars; provider webhooks (we poll). All noted as extension points in docs.
