from app.config.settings import Settings
from app.repo import b2_client


def test_settings_derives_s3_endpoint_from_b2_region():
    settings = Settings(_env_file=None, b2_region="test-region")

    assert settings.b2_endpoint == "https://s3.test-region.backblazeb2.com"


def test_s3_client_uses_standard_key_id_and_sample_user_agent(monkeypatch):
    captured = {}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return object()

    b2_client.get_s3_client.cache_clear()
    monkeypatch.setattr(b2_client.boto3, "client", fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_region", "test-region")
    monkeypatch.setattr(
        b2_client.settings, "b2_application_key_id", "application-key-id"
    )
    monkeypatch.setattr(b2_client.settings, "b2_application_key", "application-key")
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "bucket")

    try:
        b2_client.get_s3_client()
    finally:
        b2_client.get_s3_client.cache_clear()

    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == "https://s3.test-region.backblazeb2.com"
    assert captured["aws_access_key_id"] == "application-key-id"
    assert "(backblaze-b2-samples)" in captured["config"].user_agent_extra
