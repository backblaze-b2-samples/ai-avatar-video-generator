import pytest

import main as api_main
from app.config.settings import Settings
from app.repo import b2_client


def test_settings_derives_s3_endpoint_from_b2_region():
    settings = Settings(_env_file=None, b2_region="us-west-004")

    assert settings.b2_endpoint == "https://s3.us-west-004.backblazeb2.com"


def test_settings_accepts_legacy_b2_key_id_alias(monkeypatch):
    monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
    monkeypatch.setenv("B2_KEY_ID", "legacy-key-id")

    settings = Settings(_env_file=None)

    assert settings.b2_application_key_id == "legacy-key-id"


def test_settings_prefers_standard_b2_application_key_id(monkeypatch):
    monkeypatch.setenv("B2_APPLICATION_KEY_ID", "standard-key-id")
    monkeypatch.setenv("B2_KEY_ID", "legacy-key-id")

    settings = Settings(_env_file=None)

    assert settings.b2_application_key_id == "standard-key-id"


@pytest.mark.parametrize("region", ["us-west-004", "eu-central-003"])
def test_startup_validation_accepts_valid_b2_region(monkeypatch, region):
    settings = Settings(
        _env_file=None,
        b2_application_key_id="application-key-id",
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region=region,
    )
    monkeypatch.setattr(api_main, "settings", settings)

    api_main._validate_startup_configuration()


def test_startup_validation_accepts_legacy_b2_key_id(monkeypatch):
    monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
    monkeypatch.setenv("B2_KEY_ID", "legacy-key-id")
    settings = Settings(
        _env_file=None,
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region="us-west-004",
    )
    monkeypatch.setattr(api_main, "settings", settings)

    api_main._validate_startup_configuration()


def test_startup_validation_rejects_legacy_b2_key_id_placeholder(
    monkeypatch,
):
    monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
    monkeypatch.setenv("B2_KEY_ID", "your_key_id")
    settings = Settings(
        _env_file=None,
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region="us-west-004",
    )
    monkeypatch.setattr(api_main, "settings", settings)

    with pytest.raises(RuntimeError, match="placeholder values"):
        api_main._validate_startup_configuration()


@pytest.mark.parametrize(
    "region",
    [
        "https://s3.us-west-004.backblazeb2.com",
        "s3.us-west-004.backblazeb2.com",
        "us-west",
        "us_west_004",
        "US-WEST-004",
    ],
)
def test_startup_validation_rejects_malformed_b2_region(
    monkeypatch, region
):
    settings = Settings(
        _env_file=None,
        b2_application_key_id="application-key-id",
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region=region,
    )
    monkeypatch.setattr(api_main, "settings", settings)

    with pytest.raises(RuntimeError, match="Invalid B2_REGION value"):
        api_main._validate_startup_configuration()


def test_s3_client_uses_standard_key_id_and_sample_user_agent(monkeypatch):
    captured = {}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return object()

    b2_client.get_s3_client.cache_clear()
    monkeypatch.setattr(b2_client.boto3, "client", fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_region", "us-west-004")
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
    assert captured["endpoint_url"] == "https://s3.us-west-004.backblazeb2.com"
    assert captured["aws_access_key_id"] == "application-key-id"
    assert "(backblaze-b2-samples)" in captured["config"].user_agent_extra
