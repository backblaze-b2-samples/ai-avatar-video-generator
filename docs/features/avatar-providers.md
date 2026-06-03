<!-- last_verified: 2026-06-03 -->
# Feature: Pluggable Avatar Providers

## Purpose
Keep the render job provider-agnostic. The active talking-head/lip-sync provider is chosen
by config; each provider lives behind one adapter interface so adding or swapping one never
touches the service or runtime layers.

## Used By
- API/Job: `service/render.py` and the `GET /avatars` / `GET /voices` endpoints
- Config: `AVATAR_PROVIDER` selects the adapter

## Core Functions
- `services/api/app/repo/avatar_video/base.py` — `AvatarVideoProvider` protocol, `RenderResult`, `AvatarVideoError`
- `services/api/app/repo/avatar_video/__init__.py` — `get_provider()` factory (keyed on `settings.avatar_provider`)
- `services/api/app/repo/avatar_video/did_provider.py` — **default** (D-ID)
- `services/api/app/repo/avatar_video/fal_provider.py` — alternate (FAL)

## Canonical Files
- Provider interface: `services/api/app/repo/avatar_video/base.py`

## The interface
Every adapter implements:
- `list_avatars() -> list[Avatar]` — stock presenter catalog
- `list_voices() -> list[Voice]` — synced-speech voices
- `default_voice_id() -> str`
- `create_render(script, voice_id, *, provider_avatar_id?, avatar_image_bytes?) -> str` — returns a job id
- `poll_render(job_id) -> RenderResult` — one non-blocking status check (`done`/`failed`/`video_url`)

The render service owns the poll loop and the result-MP4 download; adapters only drive their
own API. Each adapter lazy-builds its HTTP client, so only the active provider needs config.

## Providers

### D-ID (default)
Real free trial through the API: 14-day trial, ~20 credits (≈5 min of video), **no credit
card**, watermarked on the trial tier. Drives `POST /talks` → poll `GET /talks/{id}` →
`result_url`. Auth is HTTP Basic with the key. Config: `AVATAR_PROVIDER=did`, `DID_API_KEY`.

### FAL (alternate)
Pay-per-use lip-sync models ($20 free signup credits). Async queue API: submit → poll status
→ fetch result. Config: `AVATAR_PROVIDER=fal`, `FAL_KEY`.

### HeyGen (extension slot — documented, not shipped)
HeyGen has the richest avatar catalog, but its API generally requires a paid plan, so it is
**not** the free default. To add it:
1. Create `repo/avatar_video/heygen_provider.py` implementing `AvatarVideoProvider`
   (HeyGen's `POST /v2/video/generate` → poll `GET /v1/video_status.get` → `video_url`).
2. Register it in `get_provider()` under `"heygen"`.
3. Add `HEYGEN_API_KEY` to `Settings` and `.env.example`.
No service/runtime changes are needed — the interface is the contract.

## Security
Provider API keys are read server-side from `Settings` only and are **never** returned to the
client. The browser only ever receives presigned B2 URLs for the finished MP4.

## Edge Cases
- Unknown `AVATAR_PROVIDER` → `AvatarVideoError` (factory rejects it)
- Missing key for the active provider → `AvatarVideoError` surfaced as 502 on `/avatars` / `/voices`
- D-ID custom-image upload → documented extension point (the default path uses a stock presenter)

## Verification
- Test files: `services/api/tests/test_render.py` uses a fake in-memory provider implementing the interface
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`

## Related Docs
- [Render job](render.md)
- [docs/SECURITY.md](../SECURITY.md)
