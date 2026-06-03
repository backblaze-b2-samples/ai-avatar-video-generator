"""Avatar-video render job orchestration — single take per render, multiple
takes per project (the iteration story).

create_project() persists script.txt (+ the uploaded avatar, if any) and the
initial manifest with one PENDING take, then returns. run_render(project_id,
take_id) is the long-running worker (kicked off via FastAPI BackgroundTasks):
it asks the provider to create a render job, polls until the job is done,
downloads the finished MP4 from the provider's result URL, stores it at
takes/<take_id>.mp4 in B2, reads its duration, and rewrites the manifest.
render_take() appends a fresh PENDING take so a user can iterate on the same
script + avatar.

Limitation: BackgroundTasks run in-process. A server restart loses in-flight
jobs (documented in docs/RELIABILITY.md). The manifest itself is durable, so a
project's completed takes always survive.
"""

import logging
import time
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    AvatarVideoError,
    download_remote,
    get_provider,
    put_bytes,
    read_object,
)
from app.service import projects as projects_service
from app.service.metadata import extract_video_duration
from app.types import (
    Avatar,
    AvatarRef,
    CreateProjectRequest,
    Project,
    ProjectDetail,
    RenderStatus,
    Take,
    Voice,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_take(provider_name: str) -> Take:
    return Take(
        take_id=str(uuid.uuid4()),
        status=RenderStatus.PENDING,
        provider=provider_name,
        created_at=_now(),
    )


def create_project(
    request: CreateProjectRequest,
    avatar_image_bytes: bytes | None = None,
    avatar_extension: str | None = None,
) -> Project:
    """Create a project, persist script + optional avatar + initial manifest.

    Does NOT render — call run_render(project.id, take.take_id) afterwards (the
    router schedules it as a background task). Exactly one avatar source is
    used: a stock presenter id (request.stock_avatar_id) or an uploaded image.
    """
    provider = get_provider()
    voice_id = request.voice_id or provider.default_voice_id()
    project_id = str(uuid.uuid4())

    if avatar_image_bytes is not None:
        image_key = projects_service.avatar_key(
            project_id, avatar_extension or "png"
        )
        avatar = AvatarRef(source="upload", image_key=image_key)
    elif request.stock_avatar_id:
        avatar = AvatarRef(
            source="stock", provider_avatar_id=request.stock_avatar_id
        )
    else:
        raise ValueError(
            "A stock avatar id or an uploaded avatar image is required."
        )

    now = _now()
    take = _new_take(provider.name)
    project = Project(
        id=project_id,
        title=request.title.strip(),
        status=RenderStatus.PENDING,
        script_source=request.script_source,
        avatar=avatar,
        voice_id=voice_id,
        takes=[take],
        created_at=now,
        updated_at=now,
    )

    # Persist durable inputs first, then the manifest (record of truth).
    put_bytes(
        request.script.encode("utf-8"),
        projects_service.script_key(project_id),
        "text/plain",
    )
    if avatar_image_bytes is not None and avatar.image_key:
        put_bytes(avatar_image_bytes, avatar.image_key, "application/octet-stream")
    projects_service.save_manifest(project)
    return project


def render_take(project_id: str) -> Take:
    """Append a new PENDING take to an existing project and persist it.

    Returns the new take so the router can schedule run_render for it.
    """
    project = projects_service.load_manifest(project_id)
    provider = get_provider()
    take = _new_take(provider.name)
    project.takes.append(take)
    project.status = RenderStatus.PENDING
    project.error = None
    _touch(project)
    return take


def _touch(project: Project) -> None:
    project.updated_at = _now()
    projects_service.save_manifest(project)


def _find_take(project: Project, take_id: str) -> Take | None:
    return next((t for t in project.takes if t.take_id == take_id), None)


def run_render(project_id: str, take_id: str) -> None:
    """Drive one take: provider create -> poll -> download MP4 -> archive to B2.

    Rewrites the manifest at each transition so progress is visible to GET
    /projects/{id} while the job is in flight.
    """
    project = projects_service.load_manifest(project_id)
    take = _find_take(project, take_id)
    if take is None:
        logger.error("run_render: take %s not found in %s", take_id, project_id)
        return

    provider = get_provider()
    take.status = RenderStatus.RENDERING
    take.error = None
    project.status = RenderStatus.RENDERING
    project.error = None
    _touch(project)

    try:
        avatar_bytes = None
        if project.avatar.source == "upload" and project.avatar.image_key:
            avatar_bytes = read_object(project.avatar.image_key)
        job_id = provider.create_render(
            _load_script(project_id),
            project.voice_id,
            provider_avatar_id=project.avatar.provider_avatar_id,
            avatar_image_bytes=avatar_bytes,
        )
        take.provider_job_id = job_id
        _touch(project)

        video_url = _poll_to_completion(provider, job_id)
        video = download_remote(video_url)
        key = projects_service.take_key(project_id, take_id)
        put_bytes(video, key, "video/mp4")

        take.video_key = key
        take.duration_seconds = extract_video_duration(video)
        take.status = RenderStatus.COMPLETE
        take.error = None
        project.status = RenderStatus.COMPLETE
        project.error = None
        _touch(project)
        logger.info(
            "Render complete: project=%s take=%s key=%s", project_id, take_id, key
        )
    except (AvatarVideoError, RuntimeError, TimeoutError) as e:
        take.status = RenderStatus.FAILED
        take.error = str(e)
        project.status = RenderStatus.FAILED
        project.error = str(e)
        _touch(project)
        logger.error("Render failed for %s/%s: %s", project_id, take_id, e)


def _poll_to_completion(provider, job_id: str) -> str:
    """Poll the provider until the job finishes; return the result MP4 url.

    Raises TimeoutError if the job runs past the configured timeout and
    AvatarVideoError if the provider reports failure.
    """
    interval = settings.avatar_poll_interval_seconds
    deadline = time.monotonic() + settings.avatar_poll_timeout_seconds
    while True:
        result = provider.poll_render(job_id)
        if result.done:
            if result.failed or not result.video_url:
                raise AvatarVideoError(
                    result.error or "Provider render failed without a result url."
                )
            return result.video_url
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Render job {job_id} did not complete within "
                f"{settings.avatar_poll_timeout_seconds:.0f}s."
            )
        time.sleep(interval)


def _load_script(project_id: str) -> str:
    raw = read_object(projects_service.script_key(project_id))
    if raw is None:
        raise RuntimeError("Project script missing from B2.")
    return raw.decode("utf-8")


def get_project_detail(project_id: str) -> ProjectDetail:
    return projects_service.get_project(project_id)


def list_avatars() -> list[Avatar]:
    """Stock avatar catalog offered by the active provider."""
    return get_provider().list_avatars()


def list_voices() -> list[Voice]:
    """Synced-speech voices offered by the active provider."""
    return get_provider().list_voices()
