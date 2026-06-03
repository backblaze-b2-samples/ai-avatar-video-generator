"""Unit tests for the D-ID adapter's create_render source handling.

D-ID supports BOTH a stock presenter and a custom photo/clip upload. These
tests stub the HTTP layer so no network is touched and assert that:
- a stock presenter id is used directly as the talk source_url,
- a custom upload is POSTed to /images first and the returned url becomes the
  talk source_url, and
- supplying neither raises AvatarVideoError.
"""

import json

import httpx
import pytest

from app.config import settings
from app.repo.avatar_video.base import AvatarVideoError
from app.repo.avatar_video.did_provider import DIDProvider


class _Resp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


class _FakeTalksClient:
    """Stub of the JSON httpx.Client returned by DIDProvider._client()."""

    def __init__(self, recorder):
        self._recorder = recorder

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, path, json=None):
        self._recorder["talks"] = {"path": path, "json": json}
        return _Resp(payload={"id": "talk-123", "status": "created"})


@pytest.fixture
def did_key(monkeypatch):
    monkeypatch.setattr(settings, "did_api_key", "test-key")


def test_create_render_uses_stock_presenter_as_source(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeTalksClient(recorder))

    job_id = provider.create_render(
        "Hello", "en-US-JennyNeural", provider_avatar_id="amy-jcwCkr1grs"
    )

    assert job_id == "talk-123"
    assert recorder["talks"]["json"]["source_url"] == "amy-jcwCkr1grs"


def test_create_render_uploads_custom_image_then_creates_talk(monkeypatch, did_key):
    recorder = {}
    provider = DIDProvider()
    monkeypatch.setattr(provider, "_client", lambda: _FakeTalksClient(recorder))

    def fake_post(url, headers=None, files=None, timeout=None):
        recorder["images"] = {"url": url, "files": files}
        return _Resp(payload={"url": "https://d-id.example/uploaded.png"})

    monkeypatch.setattr(httpx, "post", fake_post)

    job_id = provider.create_render(
        "Hello", "en-US-JennyNeural", avatar_image_bytes=b"PNGDATA"
    )

    assert job_id == "talk-123"
    # The image went to /images...
    assert recorder["images"]["url"].endswith("/images")
    # ...and its returned url became the talk source.
    assert recorder["talks"]["json"]["source_url"] == "https://d-id.example/uploaded.png"


def test_create_render_requires_a_source(monkeypatch, did_key):
    provider = DIDProvider()
    with pytest.raises(AvatarVideoError):
        provider.create_render("Hello", "en-US-JennyNeural")
