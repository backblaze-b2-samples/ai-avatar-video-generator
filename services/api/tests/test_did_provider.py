"""Unit tests for the D-ID adapter's create_render and poll_render routing.

D-ID uses two separate APIs depending on the avatar source:
- Custom uploads: POST /talks (talking-photo with source_url)
- Stock presenters: POST /clips (presenter catalog with presenter_id)

The job_id returned by create_render is prefixed ("talks:" or "clips:") so
poll_render can route to the correct endpoint.

These tests stub the HTTP layer so no network is touched.
"""

import json

import httpx
import pytest

from app.config import settings
from app.repo.avatar_video.base import AvatarVideoError
from app.repo.avatar_video.did_provider import (
    DIDProvider,
    _infer_media_type,
    _presenter_display_name,
)


class _Resp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


class _FakeApiClient:
    """Stub of the JSON httpx.Client returned by DIDProvider._client()."""

    def __init__(self, recorder):
        self._recorder = recorder

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, path, json=None):
        key = path.lstrip("/")  # "talks" or "clips"
        self._recorder[key] = {"path": path, "json": json}
        return _Resp(payload={"id": "job-123", "status": "created"})

    def get(self, path):
        self._recorder["get"] = {"path": path}
        if path == "/clips/presenters":
            return _Resp(payload=[
                {
                    "presenter_id": "v2_public_Rian_NoHands_RedJacket_Lobby@eEW_j8_sK6",
                    "thumbnail_url": "https://cdn.d-id.com/rian-thumb.jpg",
                },
                {"presenter_id": "v2_public_Amber_RedSweater_HomeOffice@atjDiWT4JK"},
            ])
        # poll path
        return _Resp(payload={"status": "done", "result_url": "https://example.com/result.mp4"})


@pytest.fixture
def did_key(monkeypatch):
    monkeypatch.setattr(settings, "did_api_key", "test-key")


# --- create_render ---

def test_create_render_stock_presenter_uses_clips_api(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeApiClient(recorder))

    job_id = provider.create_render(
        "Hello", "en-US-JennyNeural", provider_avatar_id="amy-jcwCkr1grs"
    )

    assert job_id == "clips:job-123"
    assert recorder["clips"]["json"]["presenter_id"] == "amy-jcwCkr1grs"
    assert "source_url" not in recorder["clips"]["json"]
    assert "talks" not in recorder


def test_create_render_custom_upload_uses_talks_api(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeApiClient(recorder))

    def fake_post(url, headers=None, files=None, timeout=None):
        recorder["images"] = {"url": url, "files": files}
        return _Resp(payload={"url": "https://d-id.example/uploaded.png"})

    monkeypatch.setattr(httpx, "post", fake_post)

    job_id = provider.create_render(
        "Hello", "en-US-JennyNeural", avatar_image_bytes=b"PNGDATA"
    )

    assert job_id == "talks:job-123"
    assert recorder["images"]["url"].endswith("/images")
    assert recorder["talks"]["json"]["source_url"] == "https://d-id.example/uploaded.png"
    assert "clips" not in recorder


def test_create_render_requires_a_source(monkeypatch, did_key):
    provider = DIDProvider()
    with pytest.raises(AvatarVideoError):
        provider.create_render("Hello", "en-US-JennyNeural")


# --- poll_render routing ---

def test_poll_render_clips_prefix_calls_clips_endpoint(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeApiClient(recorder))

    result = provider.poll_render("clips:job-123")

    assert recorder["get"]["path"] == "/clips/job-123"
    assert result.done
    assert result.video_url == "https://example.com/result.mp4"


def test_poll_render_talks_prefix_calls_talks_endpoint(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeApiClient(recorder))

    result = provider.poll_render("talks:job-456")

    assert recorder["get"]["path"] == "/talks/job-456"
    assert result.done


def test_poll_render_legacy_id_falls_back_to_talks(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeApiClient(recorder))

    result = provider.poll_render("legacy-id-no-prefix")

    assert recorder["get"]["path"] == "/talks/legacy-id-no-prefix"
    assert result.done


# --- list_avatars ---

def test_list_avatars_returns_presenters_from_api(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeApiClient(recorder))

    avatars = provider.list_avatars()

    assert recorder["get"]["path"] == "/clips/presenters"
    assert len(avatars) == 2
    assert avatars[0].id == "v2_public_Rian_NoHands_RedJacket_Lobby@eEW_j8_sK6"
    assert avatars[0].name == "Rian"
    assert avatars[0].source == "stock"
    assert avatars[0].thumbnail_url == "https://cdn.d-id.com/rian-thumb.jpg"
    assert avatars[1].id == "v2_public_Amber_RedSweater_HomeOffice@atjDiWT4JK"
    assert avatars[1].name == "Amber"
    assert avatars[1].thumbnail_url is None


def test_list_avatars_capped_at_five(monkeypatch, did_key):
    provider = DIDProvider()

    class _ManyPresenterClient:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def get(self, path):
            presenters = [{"presenter_id": f"v2_public_Person{i}_Suit_Office@abc"} for i in range(10)]
            return _Resp(payload=presenters)

    monkeypatch.setattr(provider, "_client", lambda: _ManyPresenterClient())
    avatars = provider.list_avatars()
    assert len(avatars) == 5


def test_list_avatars_deduplicates_by_name(monkeypatch, did_key):
    provider = DIDProvider()

    class _DupPresenterClient:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def get(self, path):
            return _Resp(payload=[
                {"presenter_id": "v2_public_Rian_RedJacket_Lobby@abc"},
                {"presenter_id": "v2_public_Rian_BlueShirt_Office@xyz"},
                {"presenter_id": "v2_public_Amber_RedSweater_Home@def"},
            ])

    monkeypatch.setattr(provider, "_client", lambda: _DupPresenterClient())
    avatars = provider.list_avatars()
    names = [a.name for a in avatars]
    assert names == ["Rian", "Amber"]


def test_list_avatars_returns_empty_on_api_error(monkeypatch, did_key):
    provider = DIDProvider()

    class _ErrorClient:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def get(self, path):
            return _Resp(status_code=403, text="Forbidden")

    monkeypatch.setattr(provider, "_client", lambda: _ErrorClient())
    assert provider.list_avatars() == []


def test_list_avatars_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "did_api_key", "")
    provider = DIDProvider()
    assert provider.list_avatars() == []


def test_list_avatars_handles_wrapped_response(monkeypatch, did_key):
    provider = DIDProvider()

    class _WrappedClient:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def get(self, path):
            return _Resp(payload={"presenters": [
                {"presenter_id": "v2_public_Adam_Suit_Office@abc123", "name": "Adam"}
            ]})

    monkeypatch.setattr(provider, "_client", lambda: _WrappedClient())
    avatars = provider.list_avatars()
    assert len(avatars) == 1
    assert avatars[0].name == "Adam"


# --- _presenter_display_name ---

def test_presenter_display_name_extracts_first_name():
    assert _presenter_display_name("v2_public_Rian_NoHands_RedJacket_Lobby@eEW_j8_sK6") == "Rian"
    assert _presenter_display_name("v2_public_Amber_RedSweater_HomeOffice@atjDiWT4JK") == "Amber"


def test_presenter_display_name_falls_back_on_unknown_format():
    assert _presenter_display_name("someid") == "Someid"


# --- image type inference ---

def test_infer_media_type_png():
    assert _infer_media_type(b"\x89PNG\r\n\x1a\n") == ("png", "image/png")


def test_infer_media_type_jpeg():
    assert _infer_media_type(b"\xff\xd8\xff\xe0") == ("jpg", "image/jpeg")


def test_infer_media_type_webp():
    assert _infer_media_type(b"RIFF\x00\x00\x00\x00WEBP") == ("webp", "image/webp")


def test_infer_media_type_mp4():
    assert _infer_media_type(b"\x00\x00\x00\x18ftyp") == ("mp4", "video/mp4")


def test_infer_media_type_unknown_falls_back_to_jpg():
    assert _infer_media_type(b"unknownbytes") == ("jpg", "image/jpeg")
