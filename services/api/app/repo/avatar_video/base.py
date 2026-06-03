"""Provider-agnostic avatar-video interface.

Each concrete adapter talks to a hosted talking-head / lip-sync API: it
submits a render job (script + avatar + voice), exposes a way to poll the
job, and hands back the URL of the finished MP4. Downloading that MP4 and
archiving it to B2 is the render service's job (repo/projects_store), not the
provider's — the provider only knows how to drive its own API.

Each adapter builds its own HTTP client lazily so importing this package never
requires a provider to be configured.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.types import Avatar, Voice


class AvatarVideoError(Exception):
    """Raised when a provider fails to submit/poll a render or is misconfigured."""


class RenderResult(BaseModel):
    """Outcome of polling a provider render job.

    `done` flips true when the provider reports completion; `video_url` is then
    the (usually short-lived) URL the render service downloads the MP4 from.
    `failed` carries a provider error message. While a job is still running,
    all three are falsy/None and the caller keeps polling.
    """

    done: bool = False
    failed: bool = False
    video_url: str | None = None
    error: str | None = None


class AvatarVideoProvider(ABC):
    """A hosted talking-head video provider (D-ID, FAL, ...)."""

    name: str = "base"

    @abstractmethod
    def list_avatars(self) -> list[Avatar]:
        """Return the provider's stock presenter/avatar catalog."""

    @abstractmethod
    def list_voices(self) -> list[Voice]:
        """Return the synced-speech voices this provider offers."""

    @abstractmethod
    def default_voice_id(self) -> str:
        """Voice id to use when the caller didn't pick one."""

    @abstractmethod
    def default_avatar_id(self) -> str | None:
        """Stock presenter id to fall back to when the caller supplied neither
        a stock avatar id nor a custom upload. None if no default is configured.
        """

    @abstractmethod
    def create_render(
        self,
        script: str,
        voice_id: str,
        *,
        provider_avatar_id: str | None = None,
        avatar_image_bytes: bytes | None = None,
    ) -> str:
        """Submit a render job and return the provider's job id.

        Exactly one of `provider_avatar_id` (a stock presenter) or
        `avatar_image_bytes` (a user-uploaded photo/clip) is supplied.
        """

    @abstractmethod
    def poll_render(self, job_id: str) -> RenderResult:
        """Check a render job's status once. Never blocks/sleeps itself."""
