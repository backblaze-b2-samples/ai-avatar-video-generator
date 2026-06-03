import pytest
from httpx import ASGITransport, AsyncClient

from app.repo.avatar_video.base import AvatarVideoProvider, RenderResult
from app.types import Avatar, Voice
from main import app


class FakeProvider(AvatarVideoProvider):
    """In-memory avatar-video provider for hermetic render tests.

    create_render returns a synthetic job id and immediately marks the job
    done on the first poll, handing back a fake result URL. Tests stub the
    MP4 download separately so no network is touched.
    """

    name = "fake"

    def __init__(self) -> None:
        self.created: list[str] = []

    def list_avatars(self):
        return [Avatar(id="stock-1", name="Stock One", source="stock")]

    def list_voices(self):
        return [Voice(id="v1", name="Voice One", description="test")]

    def default_voice_id(self):
        return "v1"

    def default_avatar_id(self):
        return None

    def create_render(
        self, script, voice_id, *, provider_avatar_id=None, avatar_image_bytes=None
    ):
        job_id = f"job-{len(self.created)}"
        self.created.append(job_id)
        return job_id

    def poll_render(self, job_id):
        return RenderResult(done=True, video_url=f"https://fake/{job_id}.mp4")


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def isolate_download_counter(tmp_path, monkeypatch):
    """Redirect the persisted download counter to a temp file per test and
    reset the in-memory counter to 0. Keeps tests hermetic and prevents
    stray writes to services/api/data/."""
    from app.config import settings
    from app.service import files as files_service

    counter_path = tmp_path / "download_count.json"
    monkeypatch.setattr(settings, "download_count_file", str(counter_path))
    monkeypatch.setattr(files_service, "_download_count", 0)
    yield
