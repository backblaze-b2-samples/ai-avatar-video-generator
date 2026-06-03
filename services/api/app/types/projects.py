from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class RenderStatus(StrEnum):
    """Lifecycle of a project and of each individual take (render).

    Single-take rendering means there is no ASSEMBLING step (unlike the
    audiobook fork's multi-chapter master): a take goes straight from
    RENDERING to COMPLETE.
    """

    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"


AvatarSource = Literal["stock", "upload"]
ScriptSource = Literal["typed", "upload"]


class Avatar(BaseModel):
    """A selectable avatar in the studio picker.

    `source="stock"` entries come from the active provider's presenter
    catalog; `source="upload"` is the synthetic option the UI renders for a
    custom photo/clip the user supplies at create time.
    """

    id: str
    name: str
    thumbnail_url: str | None = None
    source: AvatarSource = "stock"


class Voice(BaseModel):
    """A synced-speech voice offered by the active provider."""

    id: str
    name: str
    description: str | None = None
    language: str | None = None


class AvatarRef(BaseModel):
    """The avatar a project renders with, embedded in the manifest.

    A stock pick carries `provider_avatar_id`; a custom upload carries the B2
    `image_key` of the archived photo/clip under the project prefix.
    """

    source: AvatarSource
    provider_avatar_id: str | None = None
    image_key: str | None = None


class Take(BaseModel):
    """One render of the project's script + avatar.

    A project accumulates multiple takes as the user iterates; each take's MP4
    lives at `video_key` once RENDERING completes.
    """

    take_id: str
    status: RenderStatus = RenderStatus.PENDING
    provider: str
    provider_job_id: str | None = None
    video_key: str | None = None
    duration_seconds: float | None = None
    error: str | None = None
    created_at: datetime


class Project(BaseModel):
    """Full project record. This is exactly what project.json stores in B2."""

    id: str
    title: str
    status: RenderStatus = RenderStatus.PENDING
    script_source: ScriptSource = "typed"
    avatar: AvatarRef
    voice_id: str
    takes: list[Take] = []
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    @property
    def take_count(self) -> int:
        return len(self.takes)

    @property
    def renders_complete(self) -> int:
        return sum(1 for t in self.takes if t.status == RenderStatus.COMPLETE)

    @property
    def total_duration_seconds(self) -> float:
        return sum(t.duration_seconds or 0.0 for t in self.takes)

    def latest_take(self) -> Take | None:
        return self.takes[-1] if self.takes else None


class TakeDetail(BaseModel):
    take_id: str
    status: RenderStatus
    provider: str
    video_key: str | None = None
    duration_seconds: float | None = None
    duration_human: str | None = None
    error: str | None = None
    created_at: datetime


class ProjectDetail(BaseModel):
    """API response shape for a single project (mirrors the shared `Project`).

    Differs from the stored manifest by exposing derived counts + human-readable
    duration as concrete fields.
    """

    id: str
    title: str
    status: RenderStatus
    script_source: ScriptSource
    avatar: AvatarRef
    voice_id: str
    take_count: int
    renders_complete: int
    total_duration_seconds: float
    total_duration_human: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    takes: list[TakeDetail] = []


class ProjectSummary(BaseModel):
    id: str
    title: str
    status: RenderStatus
    avatar: AvatarRef
    take_count: int
    renders_complete: int
    total_duration_seconds: float
    total_duration_human: str
    created_at: datetime


class CreateProjectRequest(BaseModel):
    """Parsed multipart create payload (script text + avatar selection).

    The router validates the multipart form and builds this model; one of
    `stock_avatar_id` / an uploaded avatar file must be present.
    """

    title: str = Field(min_length=1, max_length=200)
    script: str = Field(min_length=1)
    voice_id: str | None = None
    stock_avatar_id: str | None = None
    script_source: ScriptSource = "typed"


class ProjectStats(BaseModel):
    total_projects: int
    total_renders: int
    total_duration_seconds: float
    total_duration_human: str
    total_size_bytes: int
    total_size_human: str


class DailyRendersCount(BaseModel):
    date: str
    renders: int
