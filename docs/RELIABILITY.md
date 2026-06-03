<!-- last_verified: 2026-03-06 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Render jobs (in-process)

- Renders run as FastAPI `BackgroundTasks` **in-process**. A server restart loses any
  in-flight render. The durable record is the per-project `project.json` manifest in B2 — a
  project's completed takes always survive; only takes that were mid-render at restart are
  lost (they stay `pending`/`rendering` on the manifest).
- **Recovery**: render another take from the Library to re-run the job for that project. A
  production deployment could move rendering to a durable queue/worker — noted as an
  extension point, not implemented in v1.
- **Provider rate limits / failures**: a provider error marks the take + project `failed`
  with the message on the manifest; the user can retry with another take.
- **Poll timeout**: the render poll loop gives up after `AVATAR_POLL_TIMEOUT_SECONDS`
  (default 600s) and marks the take failed rather than hanging the worker forever. Tune the
  interval/timeout via `AVATAR_POLL_INTERVAL_SECONDS` / `AVATAR_POLL_TIMEOUT_SECONDS`.
- **Download cap**: the result-MP4 download is byte-capped so a malformed/oversized result
  URL can't exhaust memory.

## Graceful Degradation

- Project/file listing returns an empty list (not an error) when B2 has no objects
- Metadata extraction failures don't block a render/upload (duration is simply null)
- A failed take never blocks the project — other takes still play, and re-rendering is one click
- Frontend shows skeleton states while loading, error states on failure, and polls in-flight renders

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
