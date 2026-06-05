"""D-ID avatar-video adapter — the default provider.

D-ID's Clips/Talks API is a good free-tier default: a 14-day trial grants ~20
credits (≈5 minutes of video) with no credit card (renders are watermarked on
the trial tier). It supports BOTH a stock presenter as the talk source AND a
custom photo/clip (D-ID's talking-photo signature capability). The flow this
adapter drives:

    POST /images          -> { "url": "<source_url>" }   (custom upload only)
    POST /talks           -> { "id": "<job>", "status": "created" }
    GET  /talks/{id}      -> { "status": "done", "result_url": "<mp4>" }  (poll)

For a stock presenter the `source_url` is the presenter id. For a custom
upload the avatar bytes are first POSTed to D-ID's `/images` endpoint to obtain
a hosted `source_url`, which is then used in the `/talks` create call — so the
studio's "upload a custom photo/clip" path renders end-to-end on the default
provider. The whole exchange is server-side; the provider key never reaches the
client.

Auth is HTTP Basic with the API key as username (D-ID's documented scheme); we
pass it through the `Authorization: Basic <base64(key:)>` header. The API key
is read from settings server-side and is never returned to the client.

`httpx` is imported lazily so the package only needs it when D-ID is active.
The custom B2 user agent lives on the boto3 client; this is an external HTTP
call to D-ID, so it carries its own descriptive User-Agent identifying the
sample.
"""

import base64
import logging

from app.config import settings
from app.repo.avatar_video.base import (
    AvatarVideoError,
    AvatarVideoProvider,
    RenderResult,
)
from app.types import Avatar, Voice

logger = logging.getLogger(__name__)


def _infer_media_type(data: bytes) -> tuple[str, str]:
    """Return (ext, mime_type) from file magic bytes; falls back to jpg."""
    if data[:4] == b"\x89PNG":
        return "png", "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return "mp4", "video/mp4"
    return "jpg", "image/jpeg"

_API_BASE = "https://api.d-id.com"
_USER_AGENT = "b2ai-avatar-video-generator (D-ID adapter)"
_TIMEOUT = 30.0
_MAX_STOCK_AVATARS = 5

# D-ID's microsoft-backed voice ids. Kept short; the default is overridable via
# AVATAR_DEFAULT_VOICE.
_VOICES = [
    Voice(id="en-US-JennyNeural", name="Jenny", description="Warm, conversational", language="en-US"),
    Voice(id="en-US-GuyNeural", name="Guy", description="Clear, confident", language="en-US"),
    Voice(id="en-GB-SoniaNeural", name="Sonia", description="British English", language="en-GB"),
]


def _presenter_display_name(presenter_id: str) -> str:
    """Extract 'Rian' from 'v2_public_Rian_NoHands_RedJacket_Lobby@eEW_j8_sK6'."""
    try:
        name_part = presenter_id.split("@")[0]
        parts = name_part.split("_")
        meaningful = [p for p in parts if p not in ("v1", "v2", "v3", "public")]
        return meaningful[0].title() if meaningful else presenter_id
    except Exception:
        return presenter_id


class DIDProvider(AvatarVideoProvider):
    name = "did"

    def __init__(self) -> None:
        self._api_key = settings.did_api_key

    def _auth_header(self) -> str:
        if not self._api_key:
            raise AvatarVideoError(
                "DID_API_KEY is not set — required for the D-ID provider."
            )
        # D-ID accepts either an already-encoded key or `key:` Basic auth.
        token = base64.b64encode(f"{self._api_key}:".encode()).decode()
        return f"Basic {token}"

    def _client(self):
        try:
            import httpx
        except ImportError as e:  # pragma: no cover - install-time guard
            raise AvatarVideoError(
                "The `httpx` package is not installed. Run `pip install httpx`."
            ) from e
        return httpx.Client(
            base_url=_API_BASE,
            timeout=_TIMEOUT,
            headers={
                "Authorization": self._auth_header(),
                "User-Agent": _USER_AGENT,
                "Content-Type": "application/json",
            },
        )

    def list_avatars(self) -> list[Avatar]:
        """Fetch the live presenter catalog from D-ID's /clips/presenters endpoint.

        D-ID's presenter IDs change across API versions and account tiers, so we
        query the catalog at runtime rather than hardcoding IDs that can go stale.
        Returns an empty list (not an error) when credentials are absent or the
        API call fails, so the studio degrades gracefully.

        Capped at _MAX_STOCK_AVATARS to keep the picker focused.
        """
        if not self._api_key:
            return []
        try:
            with self._client() as client:
                resp = client.get("/clips/presenters")
            if resp.status_code >= 400:
                logger.warning(
                    "D-ID /clips/presenters returned %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []
            data = resp.json()
            rows = data if isinstance(data, list) else data.get("presenters", [])
            result = []
            seen_names: set[str] = set()
            for p in rows:
                if len(result) >= _MAX_STOCK_AVATARS:
                    break
                pid = p.get("presenter_id") or p.get("id")
                if not pid:
                    continue
                name = (p.get("name") or _presenter_display_name(pid)).title()
                if name in seen_names:
                    continue
                seen_names.add(name)
                thumbnail = (
                    p.get("thumbnail_url")
                    or p.get("preview_url")
                    or p.get("preview_image_url")
                )
                result.append(Avatar(id=pid, name=name, thumbnail_url=thumbnail, source="stock"))
            return result
        except Exception as exc:
            logger.warning("D-ID presenter catalog fetch failed: %s", exc)
            return []

    def list_voices(self) -> list[Voice]:
        return list(_VOICES)

    def default_voice_id(self) -> str:
        return settings.avatar_default_voice or _VOICES[0].id

    def default_avatar_id(self) -> str | None:
        # Optional configured fallback presenter; None if unset (the service
        # then requires the caller to supply an avatar source).
        return settings.avatar_default_avatar or None

    def _upload_image(self, image_bytes: bytes) -> str:
        """Upload a custom avatar photo/clip to D-ID and return its source_url.

        D-ID's `/images` endpoint accepts a multipart file upload and returns a
        hosted URL we can hand to `/talks` as the talk source. This is what
        powers the studio's "upload a custom photo/clip" path. The request is
        multipart (not JSON), so it does not reuse the JSON _client(); the auth
        and User-Agent headers are applied directly.
        """
        try:
            import httpx
        except ImportError as e:  # pragma: no cover - install-time guard
            raise AvatarVideoError(
                "The `httpx` package is not installed. Run `pip install httpx`."
            ) from e
        headers = {
            "Authorization": self._auth_header(),
            "User-Agent": _USER_AGENT,
        }
        ext, mime_type = _infer_media_type(image_bytes)
        files = {"image": (f"avatar.{ext}", image_bytes, mime_type)}
        try:
            resp = httpx.post(
                f"{_API_BASE}/images",
                headers=headers,
                files=files,
                timeout=_TIMEOUT,
            )
        except Exception as e:  # network / timeout
            raise AvatarVideoError(f"D-ID image upload request failed: {e}") from e
        if resp.status_code >= 400:
            raise AvatarVideoError(
                f"D-ID image upload failed ({resp.status_code}): {resp.text[:300]}"
            )
        source_url = resp.json().get("url")
        if not source_url:
            raise AvatarVideoError("D-ID image upload returned no url.")
        return source_url

    def create_render(
        self,
        script: str,
        voice_id: str,
        *,
        provider_avatar_id: str | None = None,
        avatar_image_bytes: bytes | None = None,
    ) -> str:
        # D-ID uses two separate APIs depending on the avatar source:
        #   - Custom uploads (talking-photo): POST /talks with source_url
        #   - Stock presenters: POST /clips with presenter_id
        # The Talks API ignores presenter_id, so stock avatars must go through
        # the Clips API. The job_id is prefixed ("talks:" or "clips:") so
        # poll_render can route to the correct endpoint.
        script_block = {
            "type": "text",
            "input": script,
            "provider": {"type": "microsoft", "voice_id": voice_id},
        }
        if avatar_image_bytes is not None:
            source_url = self._upload_image(avatar_image_bytes)
            path, prefix = "/talks", "talks"
            payload = {"source_url": source_url, "script": script_block}
        elif provider_avatar_id:
            path, prefix = "/clips", "clips"
            payload = {"presenter_id": provider_avatar_id, "script": script_block}
        else:
            raise AvatarVideoError(
                "D-ID render requires a stock presenter id or a custom avatar image."
            )
        with self._client() as client:
            try:
                resp = client.post(path, json=payload)
            except Exception as e:  # network / timeout
                raise AvatarVideoError(f"D-ID {path} request failed: {e}") from e
        if resp.status_code >= 400:
            raise AvatarVideoError(
                f"D-ID {path} failed ({resp.status_code}): {resp.text[:300]}"
            )
        job_id = resp.json().get("id")
        if not job_id:
            raise AvatarVideoError(f"D-ID {path} returned no job id.")
        return f"{prefix}:{job_id}"

    def poll_render(self, job_id: str) -> RenderResult:
        if job_id.startswith("clips:"):
            path = f"/clips/{job_id[6:]}"
        elif job_id.startswith("talks:"):
            path = f"/talks/{job_id[6:]}"
        else:
            path = f"/talks/{job_id}"  # legacy ids from before the prefix scheme
        with self._client() as client:
            try:
                resp = client.get(path)
            except Exception as e:
                raise AvatarVideoError(f"D-ID poll request failed: {e}") from e
        if resp.status_code >= 400:
            raise AvatarVideoError(
                f"D-ID poll failed ({resp.status_code}): {resp.text[:300]}"
            )
        body = resp.json()
        status = body.get("status")
        if status == "done":
            return RenderResult(done=True, video_url=body.get("result_url"))
        if status in ("error", "rejected"):
            return RenderResult(
                done=True,
                failed=True,
                error=str(body.get("error") or body.get("status")),
            )
        # "created" / "started" -> still running.
        return RenderResult(done=False)
