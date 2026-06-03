"""Tests for project manifest round-trips and key/prefix validation."""

from datetime import UTC, datetime

import pytest

from app.service import projects as projects_service
from app.service.projects import (
    ProjectKeyError,
    ProjectNotFoundError,
    avatar_key,
    manifest_key,
    script_key,
    take_key,
    validate_project_id,
)
from app.types import AvatarRef, Project, RenderStatus, Take

VALID_ID = "12345678-1234-1234-1234-123456789abc"
TAKE_ID = "abcdef00-1234-1234-1234-123456789abc"


def test_key_layout():
    assert script_key(VALID_ID) == f"avatar-projects/{VALID_ID}/script.txt"
    assert manifest_key(VALID_ID) == f"avatar-projects/{VALID_ID}/project.json"
    assert avatar_key(VALID_ID, "png") == f"avatar-projects/{VALID_ID}/avatar.png"
    assert avatar_key(VALID_ID, ".JPG") == f"avatar-projects/{VALID_ID}/avatar.jpg"
    assert take_key(VALID_ID, TAKE_ID) == f"avatar-projects/{VALID_ID}/takes/{TAKE_ID}.mp4"


def test_validate_project_id_rejects_injection():
    for bad in ["", "../secrets", "not-a-uuid", "avatar-projects/x", VALID_ID + "/.."]:
        with pytest.raises(ProjectKeyError):
            validate_project_id(bad)
    validate_project_id(VALID_ID)  # valid one passes


def _stock_project(status=RenderStatus.RENDERING) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=VALID_ID,
        title="My Project",
        status=status,
        script_source="typed",
        avatar=AvatarRef(source="stock", provider_avatar_id="stock-1"),
        voice_id="v1",
        takes=[
            Take(take_id=TAKE_ID, provider="fake", created_at=now),
            Take(
                take_id="bbbbbbbb-1234-1234-1234-123456789abc",
                status=RenderStatus.COMPLETE,
                provider="fake",
                video_key=take_key(VALID_ID, "bbbbbbbb-1234-1234-1234-123456789abc"),
                duration_seconds=42.0,
                created_at=now,
            ),
        ],
        created_at=now,
        updated_at=now,
    )


def test_manifest_round_trip(monkeypatch):
    store: dict[str, dict] = {}
    monkeypatch.setattr(projects_service, "write_json", lambda k, o: store.__setitem__(k, o))
    monkeypatch.setattr(projects_service, "read_json", lambda k: store.get(k))

    projects_service.save_manifest(_stock_project())
    loaded = projects_service.load_manifest(VALID_ID)
    assert loaded.id == VALID_ID
    assert loaded.title == "My Project"
    assert loaded.take_count == 2
    assert loaded.renders_complete == 1
    assert loaded.total_duration_seconds == 42.0


def test_load_missing_manifest_raises(monkeypatch):
    monkeypatch.setattr(projects_service, "read_json", lambda k: None)
    with pytest.raises(ProjectNotFoundError):
        projects_service.load_manifest(VALID_ID)


def test_project_detail_exposes_derived_fields(monkeypatch):
    project = _stock_project(status=RenderStatus.COMPLETE)
    monkeypatch.setattr(
        projects_service, "read_json", lambda k: project.model_dump(mode="json")
    )
    detail = projects_service.get_project(VALID_ID)
    assert detail.take_count == 2
    assert detail.renders_complete == 1
    assert detail.total_duration_human == "42s"
    assert detail.avatar.provider_avatar_id == "stock-1"
    # Completed take exposes its own human duration.
    done = next(t for t in detail.takes if t.status == RenderStatus.COMPLETE)
    assert done.duration_human == "42s"


def test_list_projects_sorts_newest_first(monkeypatch):
    project = _stock_project()
    monkeypatch.setattr(
        projects_service, "list_prefixes", lambda prefix: [f"avatar-projects/{VALID_ID}/"]
    )
    monkeypatch.setattr(
        projects_service, "read_json", lambda k: project.model_dump(mode="json")
    )
    summaries = projects_service.list_projects()
    assert len(summaries) == 1
    assert summaries[0].id == VALID_ID
    assert summaries[0].take_count == 2
