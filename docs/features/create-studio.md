<!-- last_verified: 2026-06-03 -->
# Feature: New Avatar Video Studio

## Purpose
One screen to turn a script + an avatar + a voice into a render request: write or upload a
script, pick a stock avatar or upload a custom photo/clip, choose a voice, click render.

## Used By
- UI: `/create` page
- API: `GET /avatars`, `GET /voices`, `POST /projects`

## Core Functions
- `apps/web/src/components/studio/create-form.tsx` — the form + submit
- `apps/web/src/components/studio/avatar-picker.tsx` — stock grid + "upload custom" tile
- `apps/web/src/components/studio/voice-picker.tsx` — voice `<select>`
- `apps/web/src/lib/queries.ts` — `useAvatars()`, `useVoices()`, `useCreateProject()`
- `apps/web/src/lib/api-client.ts` — `createProject()` (multipart FormData)
- `services/api/app/runtime/projects.py` — `POST /projects` multipart handler
- `services/api/app/service/render.py` — `create_project()`

## Canonical Files
- Studio form: `apps/web/src/components/studio/create-form.tsx`
- Create handler: `services/api/app/runtime/projects.py`

## Inputs
- title: string (form)
- script: string — typed in the textarea or loaded from a `.txt` file
- voice_id: string (optional; defaults to the provider's default voice)
- avatar: a stock avatar id **or** an uploaded photo/clip file (exactly one required)
- script_source: `typed | upload`

## Outputs
- `POST /projects` (multipart) → `202` + `ProjectDetail` (with one pending take)
- Side effects: writes `script.txt`, the optional `avatar.<ext>`, and `project.json` to B2;
  schedules the background render
- Navigation: on success the studio routes to `/library?project=<id>`

## Flow
- The avatar picker loads the stock catalog from `GET /avatars`; the voice picker loads
  `GET /voices`
- The user types/uploads a script, picks an avatar (or uploads one), picks a voice
- Submit posts multipart form data; the API validates that exactly one avatar source is
  present, persists inputs, and returns the project with a pending take
- The studio redirects to the project in the Library, where the in-flight take renders

## Edge Cases
- No avatar selected → submit is disabled; the API also 400s if neither source is present
- Unsupported avatar file type → client rejects with a toast (PNG/JPEG/WEBP/MP4/MOV only)
- Provider key missing → `GET /avatars` / `GET /voices` 502; pickers show a hint
- Empty title or script → submit disabled

## UX States
- Loading: skeletons in the avatar/voice pickers
- Error: inline hint when the provider catalog is unavailable
- Submitting: button shows "Starting…" and is disabled

## Verification
- Test files: `services/api/tests/test_render.py` (create_project, uploaded avatar archiving)
- Required cases: stock avatar create, uploaded avatar create, missing avatar rejection
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Render job](render.md)
- [Scoped Library](library.md)
- [Pluggable avatar providers](avatar-providers.md)
- [App Workflows](../app-workflows.md)
