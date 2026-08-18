<!-- last_verified: 2026-04-22 -->
# Security

Security principles and implementation for the ai-avatar-video-generator.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`,
  signature v4
- **API -> avatar provider**: Authenticated via a server-side key (`DID_API_KEY` / `FAL_KEY`); see below
- **Client -> B2**: Presigned GET URLs (short expiry) — inline disposition for `<video>`
  streaming of takes, forced attachment for downloads

## Provider key handling

- `DID_API_KEY` / `FAL_KEY` are read server-side from `Settings` (pydantic-settings) and are
  **never** returned to the client. The browser only ever receives presigned B2 URLs.
- All provider HTTP calls (create, poll) and the result-MP4 download happen server-side in
  the `repo/avatar_video/` adapters and `repo/projects_store.py`.
- Adding a provider (e.g. HeyGen) follows the same rule: read its key from `Settings`, keep
  it in the adapter, never surface it on an API response.

## Avatar-upload validation

- The avatar dropzone accepts only PNG/JPEG/WEBP photos and MP4/MOV clips (checked client-side)
- The create endpoint streams the uploaded avatar in chunks with the same 100MB cap as the
  generic upload, and stores it under the project prefix (`avatar-projects/<id>/avatar.<ext>`)
- The avatar file extension is mapped through a fixed allowlist before becoming a B2 key

## Key / prefix validation

- Project and take ids are validated against a strict UUID regex before becoming B2 keys
  (`service/projects.py::validate_project_id` / `validate_take_id`) — guards key injection
- The Library is scoped to the `avatar-projects/` prefix; the kept File Explorer's
  `validate_key` still guards the full-bucket routes (path traversal, null bytes, etc.)

## Presigned-URL reads

- Take streaming uses a short-lived presigned GET **without** forced attachment so the
  browser can issue Range reads into `<video>`; downloads use a presigned GET **with**
  `Content-Disposition: attachment`. Both expire quickly and are cheap to regenerate.

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- B2 configuration uses the standardized names in `.env.example`:
  `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, and
  optional `B2_PUBLIC_URL_BASE`
- Never committed to source control
- `.env.example` documents required variables without values (B2 + provider keys)

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
