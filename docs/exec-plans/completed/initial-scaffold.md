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
1. S3 API is the default — boto3 only in `repo/b2_client.py`; no b2-native SDK. The provider
   result-MP4 download is a plain HTTP GET (`httpx`) in the repo layer — not an S3 op.
2. Custom user agent on the S3 client — `user_agent_extra="b2ai-avatar-video-generator"`.
3. Standardized B2 env names — `B2_ENDPOINT`, `B2_REGION`, `B2_KEY_ID`, `B2_APPLICATION_KEY`,
   `B2_BUCKET_NAME` (+ optional `B2_PUBLIC_URL`).

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
