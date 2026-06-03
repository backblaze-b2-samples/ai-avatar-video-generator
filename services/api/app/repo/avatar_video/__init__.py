"""Avatar-video provider factory.

Selects the concrete adapter from `settings.avatar_provider` (default `did`).
Adapters are constructed lazily so importing this package never builds an HTTP
client or requires a provider key.

HeyGen is a documented third adapter slot (see
docs/features/avatar-providers.md): its API generally needs a paid plan, so it
is not the free default and ships as an extension point only.
"""

from app.config import settings
from app.repo.avatar_video.base import (
    AvatarVideoError,
    AvatarVideoProvider,
    RenderResult,
)

_DEFAULT = "did"


def get_provider(name: str | None = None) -> AvatarVideoProvider:
    provider = (name or settings.avatar_provider or _DEFAULT).strip().lower()
    if provider == "did":
        from app.repo.avatar_video.did_provider import DIDProvider

        return DIDProvider()
    if provider == "fal":
        from app.repo.avatar_video.fal_provider import FALProvider

        return FALProvider()
    raise AvatarVideoError(
        f"Unknown avatar provider '{provider}'. Supported: did, fal."
    )


__all__ = [
    "AvatarVideoError",
    "AvatarVideoProvider",
    "RenderResult",
    "get_provider",
]
