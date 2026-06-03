<!-- last_verified: 2026-06-03 -->
# Feature: Take Metadata

## Purpose
Compute a checksum for every file and, for rendered takes (MP4s), the playback duration —
without decoding the video or shelling out to ffmpeg.

## Used By
- API: `POST /upload` (kept generic upload) and the render job (`service/render.run_render`)
- UI: upload results, the file metadata panel

## Core Functions
- `services/api/app/service/metadata.py` — `extract_metadata()`, `extract_video_duration()`, `_find_atom()`
- `apps/web/src/components/files/file-metadata-panel.tsx` — displays metadata in a card

## Canonical Files
- Metadata extraction pattern: `services/api/app/service/metadata.py`
- Metadata display component: `apps/web/src/components/files/file-metadata-panel.tsx`

## Inputs
- file_data: bytes
- filename: string
- content_type: string

## Outputs
- `FileMetadataDetail`: filename, size_bytes, size_human, mime_type, extension, md5, sha256, uploaded_at
- Video-specific (optional): duration_seconds, duration_human

## Flow
- Compute MD5 and SHA-256 over the bytes
- If the content type is `video/*` (or the extension is `mp4`/`mov`/`m4v`), call
  `extract_video_duration()`
- `extract_video_duration()` walks the MP4 atom tree (`moov` → `mvhd`), reads the
  timescale + duration fields from the movie header, and returns `duration / timescale`.
  This is header-only (no decode, no ffmpeg) and cheap enough to run inline on every render.
- The render job stores the duration on the take so the Library and dashboard can show it.

## Edge Cases
- Non-MP4 / fragmented MP4 with no top-level `mvhd` → duration is null (panel hides the row)
- Truncated/corrupt header → parse fails silently, duration null, warning logged
- Non-video upload → only the common fields (hashes, size, extension) are populated

## UX States
- Not applicable (metadata is part of the upload response and the file preview)

## Verification
- Test files: covered indirectly via `services/api/tests/test_render.py` (duration is stubbed
  there; the parser itself is pure and can be unit-tested directly)
- Required cases: MP4 with a v0 `mvhd`, MP4 with a v1 (64-bit) `mvhd`, non-video bytes
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Extension points
- Resolution / codec / bitrate are intentionally out of scope (they would need a real
  demuxer). Add a dedicated probe library in `repo/` if a future feature needs them.

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Render job](render.md)
- [File Upload](file-upload.md)
