"""Tests for render orchestration with a fake provider and in-memory B2 store."""

from datetime import UTC, datetime

from app.service import render as render_service
from app.types import CreateProjectRequest, RenderStatus

from .conftest import FakeProvider


def _install_fakes(monkeypatch, provider=None):
    """Wire render + projects to an in-memory B2 store and a fake provider.

    The provider's result URL is never fetched over the network: download_remote
    is stubbed to return fake MP4 bytes, and duration extraction returns a fixed
    value so the assertions are deterministic.
    """
    objects: dict[str, bytes] = {}
    manifests: dict[str, dict] = {}
    provider = provider or FakeProvider()

    monkeypatch.setattr(render_service, "get_provider", lambda: provider)
    monkeypatch.setattr(
        render_service, "put_bytes", lambda data, key, ct: objects.__setitem__(key, data)
    )
    monkeypatch.setattr(render_service, "read_object", lambda key: objects.get(key))
    monkeypatch.setattr(render_service, "download_remote", lambda url: b"FAKE-MP4-BYTES")
    monkeypatch.setattr(render_service, "extract_video_duration", lambda data: 12.0)

    from app.service import projects as projects_service

    monkeypatch.setattr(projects_service, "write_json", lambda k, o: manifests.__setitem__(k, o))
    monkeypatch.setattr(projects_service, "read_json", lambda k: manifests.get(k))
    return objects, manifests


def _request(**kw):
    base = dict(title="Test", script="Hello world from the avatar.", stock_avatar_id="stock-1")
    base.update(kw)
    return CreateProjectRequest(**base)


def test_create_project_writes_script_and_manifest(monkeypatch):
    objects, manifests = _install_fakes(monkeypatch)
    project = render_service.create_project(_request())
    assert project.status == RenderStatus.PENDING
    assert project.take_count == 1
    assert project.voice_id == "v1"
    assert project.avatar.provider_avatar_id == "stock-1"
    assert any(k.endswith("script.txt") for k in objects)
    assert any(k.endswith("project.json") for k in manifests)


def test_create_project_archives_uploaded_avatar(monkeypatch):
    objects, _ = _install_fakes(monkeypatch)
    project = render_service.create_project(
        _request(stock_avatar_id=None), avatar_image_bytes=b"IMG", avatar_extension="png"
    )
    assert project.avatar.source == "upload"
    assert project.avatar.image_key is not None
    assert objects.get(project.avatar.image_key) == b"IMG"


def test_create_project_falls_back_to_default_avatar(monkeypatch):
    """With neither a stock id nor an upload, AVATAR_DEFAULT_AVATAR is used."""

    class DefaultAvatarProvider(FakeProvider):
        def default_avatar_id(self):
            return "default-presenter"

    _install_fakes(monkeypatch, provider=DefaultAvatarProvider())
    project = render_service.create_project(_request(stock_avatar_id=None))
    assert project.avatar.source == "stock"
    assert project.avatar.provider_avatar_id == "default-presenter"


def test_create_project_requires_avatar_when_no_default(monkeypatch):
    """No stock id, no upload, no configured default -> ValueError."""
    import pytest

    _install_fakes(monkeypatch)  # FakeProvider.default_avatar_id() is None
    with pytest.raises(ValueError):
        render_service.create_project(_request(stock_avatar_id=None))


def test_run_render_downloads_and_archives_take(monkeypatch):
    objects, _ = _install_fakes(monkeypatch)
    project = render_service.create_project(_request())
    take_id = project.takes[0].take_id

    render_service.run_render(project.id, take_id)

    final = render_service.get_project_detail(project.id)
    assert final.status == RenderStatus.COMPLETE
    assert final.renders_complete == 1
    assert final.total_duration_seconds == 12.0
    # The MP4 landed under takes/.
    assert any(k.endswith(f"takes/{take_id}.mp4") for k in objects)


def test_render_take_appends_iteration(monkeypatch):
    _install_fakes(monkeypatch)
    project = render_service.create_project(_request())
    render_service.run_render(project.id, project.takes[0].take_id)

    take = render_service.render_take(project.id)
    render_service.run_render(project.id, take.take_id)

    final = render_service.get_project_detail(project.id)
    assert final.take_count == 2
    assert final.renders_complete == 2


def test_run_render_marks_failed_on_provider_error(monkeypatch):
    from app.repo.avatar_video.base import AvatarVideoError, RenderResult

    class BoomProvider(FakeProvider):
        def poll_render(self, job_id):
            return RenderResult(done=True, failed=True, error="provider down")

    _install_fakes(monkeypatch, provider=BoomProvider())
    project = render_service.create_project(_request())
    render_service.run_render(project.id, project.takes[0].take_id)

    final = render_service.get_project_detail(project.id)
    assert final.status == RenderStatus.FAILED
    assert "provider down" in (final.error or "")
    # Sanity: AvatarVideoError is importable and used in the failure path.
    assert AvatarVideoError is not None


def test_list_avatars_and_voices_use_provider(monkeypatch):
    monkeypatch.setattr(render_service, "get_provider", lambda: FakeProvider())
    assert render_service.list_avatars()[0].id == "stock-1"
    assert render_service.list_voices()[0].id == "v1"


def test_created_at_is_utc_timestamp(monkeypatch):
    _install_fakes(monkeypatch)
    project = render_service.create_project(_request())
    assert isinstance(project.created_at, datetime)
    assert project.created_at.tzinfo is UTC
