"""Avatar-video project manifest CRUD over B2.

B2 is the sole datastore. Each project lives under `avatar-projects/<id>/`:

    avatar-projects/<id>/project.json         job + take state (record of truth)
    avatar-projects/<id>/script.txt           durable script text
    avatar-projects/<id>/avatar.<ext>         custom avatar (only when uploaded)
    avatar-projects/<id>/takes/<take_id>.mp4  each rendered take (the iteration story)

The manifest *is* the Project model serialized to JSON. There is no database.
"""

import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.repo import (
    delete_prefix,
    get_presigned_url,
    get_stream_url,
    list_prefixes,
    prefix_size,
    read_json,
    write_json,
)
from app.types import (
    DailyRendersCount,
    Project,
    ProjectDetail,
    ProjectStats,
    ProjectSummary,
    RenderStatus,
    TakeDetail,
)
from app.types.formatting import humanize_bytes, humanize_duration

ROOT_PREFIX = "avatar-projects/"
_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


class ProjectKeyError(Exception):
    """Raised when a project/take id is malformed (guards key injection)."""

    def __init__(self, detail: str = "Invalid project id"):
        self.detail = detail
        super().__init__(detail)


class ProjectNotFoundError(Exception):
    def __init__(self, detail: str = "Project not found"):
        self.detail = detail
        super().__init__(detail)


def validate_project_id(project_id: str) -> None:
    if not project_id or not _ID_RE.match(project_id):
        raise ProjectKeyError()


def validate_take_id(take_id: str) -> None:
    if not take_id or not _ID_RE.match(take_id):
        raise ProjectKeyError("Invalid take id")


def project_prefix(project_id: str) -> str:
    return f"{ROOT_PREFIX}{project_id}/"


def script_key(project_id: str) -> str:
    return f"{project_prefix(project_id)}script.txt"


def manifest_key(project_id: str) -> str:
    return f"{project_prefix(project_id)}project.json"


def avatar_key(project_id: str, extension: str) -> str:
    ext = extension.lstrip(".").lower() or "bin"
    return f"{project_prefix(project_id)}avatar.{ext}"


def take_key(project_id: str, take_id: str) -> str:
    return f"{project_prefix(project_id)}takes/{take_id}.mp4"


def save_manifest(project: Project) -> None:
    """Persist the Project manifest to B2 (the single write that records state)."""
    write_json(manifest_key(project.id), project.model_dump(mode="json"))


def load_manifest(project_id: str) -> Project:
    validate_project_id(project_id)
    raw = read_json(manifest_key(project_id))
    if raw is None:
        raise ProjectNotFoundError()
    return Project.model_validate(raw)


def _to_detail(project: Project) -> ProjectDetail:
    return ProjectDetail(
        id=project.id,
        title=project.title,
        status=project.status,
        script_source=project.script_source,
        avatar=project.avatar,
        voice_id=project.voice_id,
        take_count=project.take_count,
        renders_complete=project.renders_complete,
        total_duration_seconds=project.total_duration_seconds,
        total_duration_human=humanize_duration(project.total_duration_seconds),
        created_at=project.created_at,
        updated_at=project.updated_at,
        error=project.error,
        takes=[
            TakeDetail(
                take_id=t.take_id,
                status=t.status,
                provider=t.provider,
                video_key=t.video_key,
                duration_seconds=t.duration_seconds,
                duration_human=(
                    humanize_duration(t.duration_seconds)
                    if t.duration_seconds is not None
                    else None
                ),
                error=t.error,
                created_at=t.created_at,
            )
            for t in project.takes
        ],
    )


def get_project(project_id: str) -> ProjectDetail:
    return _to_detail(load_manifest(project_id))


def take_stream_url(project_id: str, take_id: str) -> str:
    """Presigned inline (non-attachment) URL for streaming a rendered take."""
    validate_take_id(take_id)
    project = load_manifest(project_id)
    match = next((t for t in project.takes if t.take_id == take_id), None)
    if match is None or not match.video_key:
        raise ProjectNotFoundError("Take video not available yet")
    return get_stream_url(match.video_key)


def take_download_url(project_id: str, take_id: str) -> str:
    """Presigned attachment URL for downloading a rendered take MP4."""
    validate_take_id(take_id)
    project = load_manifest(project_id)
    match = next((t for t in project.takes if t.take_id == take_id), None)
    if match is None or not match.video_key:
        raise ProjectNotFoundError("Take video not available yet")
    safe_title = re.sub(r"[^\w\- ]+", "", project.title).strip() or "take"
    return get_presigned_url(
        match.video_key, filename=f"{safe_title}-{take_id[:8]}.mp4"
    )


def _id_from_prefix(prefix: str) -> str:
    # "avatar-projects/<id>/" -> "<id>"
    return prefix[len(ROOT_PREFIX):].rstrip("/")


def _iter_projects():
    """Yield every stored Project by scanning the scoped prefix + manifests."""
    for prefix in list_prefixes(ROOT_PREFIX):
        project_id = _id_from_prefix(prefix)
        raw = read_json(manifest_key(project_id))
        if raw is None:
            continue
        yield Project.model_validate(raw)


def list_projects() -> list[ProjectSummary]:
    """Scan `avatar-projects/` folders and read each manifest into a summary."""
    summaries = [
        ProjectSummary(
            id=p.id,
            title=p.title,
            status=p.status,
            avatar=p.avatar,
            take_count=p.take_count,
            renders_complete=p.renders_complete,
            total_duration_seconds=p.total_duration_seconds,
            total_duration_human=humanize_duration(p.total_duration_seconds),
            created_at=p.created_at,
        )
        for p in _iter_projects()
    ]
    summaries.sort(key=lambda p: p.created_at, reverse=True)
    return summaries


def delete_project(project_id: str) -> int:
    validate_project_id(project_id)
    # Ensure it exists first so a bad id 404s rather than silently no-ops.
    load_manifest(project_id)
    return delete_prefix(project_prefix(project_id))


def project_stats() -> ProjectStats:
    """Aggregate counts across every project for the dashboard."""
    total_projects = 0
    total_renders = 0
    total_duration = 0.0
    for project in _iter_projects():
        total_projects += 1
        total_renders += project.renders_complete
        total_duration += project.total_duration_seconds
    total_size = prefix_size(ROOT_PREFIX)
    return ProjectStats(
        total_projects=total_projects,
        total_renders=total_renders,
        total_duration_seconds=total_duration,
        total_duration_human=humanize_duration(total_duration),
        total_size_bytes=total_size,
        total_size_human=humanize_bytes(total_size),
    )


def project_activity(days: int = 7) -> list[DailyRendersCount]:
    """Completed renders per day over the last N days (dashboard chart).

    Attributes each completed take to the take's creation day — a simple,
    explainable proxy for "renders produced per day".
    """
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    renders_by_day: dict[str, int] = defaultdict(int)
    for project in _iter_projects():
        for take in project.takes:
            if take.status != RenderStatus.COMPLETE:
                continue
            d = take.created_at.date()
            if d >= cutoff:
                renders_by_day[d.isoformat()] += 1
    return [
        DailyRendersCount(
            date=(cutoff + timedelta(days=i)).isoformat(),
            renders=renders_by_day.get(
                (cutoff + timedelta(days=i)).isoformat(), 0
            ),
        )
        for i in range(days)
    ]
