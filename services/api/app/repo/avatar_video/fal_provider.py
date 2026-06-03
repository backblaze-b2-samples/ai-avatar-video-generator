"""FAL avatar-video adapter — optional alternate provider.

NOT the default. Set AVATAR_PROVIDER=fal and provide FAL_KEY to use it. FAL
hosts pay-per-use lip-sync models (e.g. `veed/lipsync`, `sadtalker`) that take
an avatar image plus an audio/text input and return an MP4. FAL exposes an
async queue API:

    POST   /<model>            (submit)  -> { "request_id": "<id>" }
    GET    /<model>/requests/<id>/status -> { "status": "COMPLETED" | ... }
    GET    /<model>/requests/<id>        -> { "video": { "url": "<mp4>" } }

This adapter is a working skeleton against that shape. `httpx` is imported
lazily. The API key is read server-side and never returned to the client.
"""

from app.config import settings
from app.repo.avatar_video.base import (
    AvatarVideoError,
    AvatarVideoProvider,
    RenderResult,
)
from app.types import Avatar, Voice

_API_BASE = "https://queue.fal.run"
_MODEL = "veed/lipsync"
_USER_AGENT = "b2ai-avatar-video-generator (FAL adapter)"
_TIMEOUT = 30.0

# FAL lip-sync models drive a user-supplied avatar image, so the stock catalog
# is intentionally small; custom uploads are the primary path here.
_STOCK_AVATARS = [
    Avatar(id="fal-presenter-01", name="Presenter A", source="stock"),
]

_VOICES = [
    Voice(id="fal-default", name="Default", description="Model default voice"),
]


class FALProvider(AvatarVideoProvider):
    name = "fal"

    def __init__(self) -> None:
        self._api_key = settings.fal_key

    def _client(self):
        if not self._api_key:
            raise AvatarVideoError(
                "FAL_KEY is not set — required for the FAL provider."
            )
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
                "Authorization": f"Key {self._api_key}",
                "User-Agent": _USER_AGENT,
                "Content-Type": "application/json",
            },
        )

    def list_avatars(self) -> list[Avatar]:
        return list(_STOCK_AVATARS)

    def list_voices(self) -> list[Voice]:
        return list(_VOICES)

    def default_voice_id(self) -> str:
        return settings.avatar_default_voice or _VOICES[0].id

    def default_avatar_id(self) -> str | None:
        # Optional configured fallback presenter; None if unset.
        return settings.avatar_default_avatar or None

    def create_render(
        self,
        script: str,
        voice_id: str,
        *,
        provider_avatar_id: str | None = None,
        avatar_image_bytes: bytes | None = None,
    ) -> str:
        # FAL's lip-sync models want a publicly reachable avatar image URL plus
        # the spoken text/audio. Uploading the avatar bytes to FAL's storage
        # (fal.storage) is the documented extension point; here we accept a
        # presenter id as the image reference so the skeleton is runnable.
        if not (provider_avatar_id or avatar_image_bytes):
            raise AvatarVideoError("FAL render requires an avatar image.")
        payload = {
            "text": script,
            "voice": voice_id,
            "avatar": provider_avatar_id,
        }
        with self._client() as client:
            try:
                resp = client.post(f"/{_MODEL}", json=payload)
            except Exception as e:
                raise AvatarVideoError(f"FAL submit request failed: {e}") from e
        if resp.status_code >= 400:
            raise AvatarVideoError(
                f"FAL submit failed ({resp.status_code}): {resp.text[:300]}"
            )
        request_id = resp.json().get("request_id")
        if not request_id:
            raise AvatarVideoError("FAL submit returned no request_id.")
        return request_id

    def poll_render(self, job_id: str) -> RenderResult:
        with self._client() as client:
            try:
                status_resp = client.get(f"/{_MODEL}/requests/{job_id}/status")
            except Exception as e:
                raise AvatarVideoError(f"FAL status request failed: {e}") from e
            if status_resp.status_code >= 400:
                raise AvatarVideoError(
                    f"FAL status failed ({status_resp.status_code}): "
                    f"{status_resp.text[:300]}"
                )
            status = status_resp.json().get("status")
            if status in ("IN_QUEUE", "IN_PROGRESS"):
                return RenderResult(done=False)
            if status != "COMPLETED":
                return RenderResult(done=True, failed=True, error=str(status))
            # Completed — fetch the result payload for the MP4 url.
            try:
                result = client.get(f"/{_MODEL}/requests/{job_id}")
            except Exception as e:
                raise AvatarVideoError(f"FAL result request failed: {e}") from e
        if result.status_code >= 400:
            raise AvatarVideoError(
                f"FAL result failed ({result.status_code}): {result.text[:300]}"
            )
        video = result.json().get("video") or {}
        return RenderResult(done=True, video_url=video.get("url"))
