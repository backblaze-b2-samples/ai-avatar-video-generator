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

from app.config import settings
from app.repo.avatar_video.base import (
    AvatarVideoError,
    AvatarVideoProvider,
    RenderResult,
)
from app.types import Avatar, Voice

_API_BASE = "https://api.d-id.com"
_USER_AGENT = "b2ai-avatar-video-generator (D-ID adapter)"
_TIMEOUT = 30.0

# A small curated slice of D-ID's stock presenter catalog. The full catalog is
# large and account-tier dependent; these stable presenter ids give the studio
# a working picker out of the box without an extra catalog round-trip.
_STOCK_AVATARS = [
    Avatar(id="amy-jcwCkr1grs", name="Amy", source="stock"),
    Avatar(id="noelle-AQ2mVbvT", name="Noelle", source="stock"),
    Avatar(id="rian-lZC6MmWfC", name="Rian", source="stock"),
]

# D-ID's microsoft-backed voice ids. Kept short; the default is overridable via
# AVATAR_DEFAULT_VOICE.
_VOICES = [
    Voice(id="en-US-JennyNeural", name="Jenny", description="Warm, conversational", language="en-US"),
    Voice(id="en-US-GuyNeural", name="Guy", description="Clear, confident", language="en-US"),
    Voice(id="en-GB-SoniaNeural", name="Sonia", description="British English", language="en-GB"),
]


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
        return list(_STOCK_AVATARS)

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
        files = {"image": ("avatar", image_bytes, "application/octet-stream")}
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
        # D-ID's create-talk takes a `source_url` (image/clip) plus a `script`
        # with a TTS voice. The source_url is either a stock presenter id or,
        # for a custom upload (D-ID's talking-photo capability), a URL obtained
        # by first POSTing the avatar bytes to D-ID's /images endpoint.
        if avatar_image_bytes is not None:
            source_url = self._upload_image(avatar_image_bytes)
        elif provider_avatar_id:
            source_url = provider_avatar_id
        else:
            raise AvatarVideoError(
                "D-ID render requires a stock presenter id or a custom avatar image."
            )
        payload = {
            "source_url": source_url,
            "script": {
                "type": "text",
                "input": script,
                "provider": {"type": "microsoft", "voice_id": voice_id},
            },
        }
        with self._client() as client:
            try:
                resp = client.post("/talks", json=payload)
            except Exception as e:  # network / timeout
                raise AvatarVideoError(f"D-ID create-talk request failed: {e}") from e
        if resp.status_code >= 400:
            raise AvatarVideoError(
                f"D-ID create-talk failed ({resp.status_code}): {resp.text[:300]}"
            )
        job_id = resp.json().get("id")
        if not job_id:
            raise AvatarVideoError("D-ID create-talk returned no job id.")
        return job_id

    def poll_render(self, job_id: str) -> RenderResult:
        with self._client() as client:
            try:
                resp = client.get(f"/talks/{job_id}")
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
