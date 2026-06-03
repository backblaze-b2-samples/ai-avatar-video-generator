from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    b2_endpoint: str = ""
    b2_region: str = ""
    b2_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url: str = ""

    # Avatar-video providers. The active adapter is chosen by `avatar_provider`;
    # its SDK/HTTP client is built by the matching adapter in repo/avatar_video/.
    # Provider API keys are server-side only and never exposed to the client.
    avatar_provider: str = "did"
    did_api_key: str = ""
    fal_key: str = ""
    avatar_default_voice: str = ""
    avatar_default_avatar: str = ""
    # Render poll loop: how often to ask the provider for job status, and how
    # long to wait before giving up (a single MP4 render can take minutes).
    avatar_poll_interval_seconds: float = 3.0
    avatar_poll_timeout_seconds: float = 600.0

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
