import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from app.config import settings
from app.repo import AvatarVideoError
from app.service.projects import (
    ProjectKeyError,
    ProjectNotFoundError,
    delete_project,
    get_project,
    list_projects,
    project_activity,
    project_stats,
    take_download_url,
    take_stream_url,
)
from app.service.render import (
    create_project,
    get_project_detail,
    list_avatars,
    list_voices,
    render_take,
    run_render,
)
from app.types import (
    Avatar,
    CreateProjectRequest,
    DailyRendersCount,
    ProjectDetail,
    ProjectStats,
    ProjectSummary,
    Voice,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_AVATAR_EXTS = {"png": "png", "jpg": "jpg", "jpeg": "jpg", "webp": "webp", "mp4": "mp4", "mov": "mov"}


@router.get("/avatars", response_model=list[Avatar])
async def list_avatars_endpoint():
    try:
        return list_avatars()
    except AvatarVideoError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None


@router.get("/voices", response_model=list[Voice])
async def list_voices_endpoint():
    try:
        return list_voices()
    except AvatarVideoError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects_endpoint():
    return list_projects()


@router.get("/projects/stats", response_model=ProjectStats)
async def project_stats_endpoint():
    return project_stats()


@router.get("/projects/stats/activity", response_model=list[DailyRendersCount])
async def project_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return project_activity(days=days)


@router.post("/projects", response_model=ProjectDetail, status_code=202)
async def create_project_endpoint(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    script: str = Form(...),
    voice_id: str | None = Form(None),
    stock_avatar_id: str | None = Form(None),
    script_source: str = Form("typed"),
    avatar: UploadFile | None = File(None),
):
    avatar_bytes: bytes | None = None
    avatar_ext: str | None = None
    if avatar is not None and avatar.filename:
        avatar_bytes = await _read_capped(avatar)
        ext = avatar.filename.rsplit(".", 1)[-1].lower() if "." in avatar.filename else ""
        avatar_ext = _AVATAR_EXTS.get(ext, "png")
    if avatar_bytes is None and not stock_avatar_id:
        raise HTTPException(
            status_code=400,
            detail="Provide a stock avatar id or upload an avatar image.",
        )

    try:
        request = CreateProjectRequest(
            title=title,
            script=script,
            voice_id=voice_id or None,
            stock_avatar_id=stock_avatar_id or None,
            script_source="upload" if script_source == "upload" else "typed",
        )
        project = create_project(request, avatar_bytes, avatar_ext)
    except AvatarVideoError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    take = project.takes[0]
    background_tasks.add_task(run_render, project.id, take.take_id)
    logger.info("Project created: id=%s take=%s", project.id, take.take_id)
    return get_project_detail(project.id)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project_endpoint(project_id: str):
    try:
        return get_project(project_id)
    except ProjectKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post(
    "/projects/{project_id}/takes", response_model=ProjectDetail, status_code=202
)
async def render_take_endpoint(project_id: str, background_tasks: BackgroundTasks):
    try:
        take = render_take(project_id)
    except ProjectKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except AvatarVideoError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
    background_tasks.add_task(run_render, project_id, take.take_id)
    logger.info("Take queued: project=%s take=%s", project_id, take.take_id)
    return get_project_detail(project_id)


@router.delete("/projects/{project_id}")
async def delete_project_endpoint(project_id: str):
    try:
        deleted = delete_project(project_id)
    except ProjectKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    logger.info("Project deleted: id=%s objects=%d", project_id, deleted)
    return {"deleted": True, "id": project_id, "objects_removed": deleted}


@router.get("/projects/{project_id}/takes/{take_id}/video")
async def take_video_endpoint(project_id: str, take_id: str, download: bool = False):
    try:
        url = (
            take_download_url(project_id, take_id)
            if download
            else take_stream_url(project_id, take_id)
        )
    except ProjectKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url}


async def _read_capped(upload: UploadFile) -> bytes:
    """Read an uploaded avatar with chunked streaming + early size rejection."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Avatar file too large")
        chunks.append(chunk)
    return b"".join(chunks)
