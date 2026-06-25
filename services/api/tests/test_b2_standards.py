from pathlib import Path

import pytest

import main as api_main
from app.config.settings import (
    B2_ENV_CONTRACT,
    B2_PLACEHOLDER_VALUES,
    Settings,
)
from app.repo import b2_client

REPO_ROOT = Path(__file__).resolve().parents[3]


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


def test_settings_ignores_legacy_dotenv_keys(monkeypatch, tmp_path):
    for key in (
        "B2_REGION",
        "B2_APPLICATION_KEY_ID",
        "B2_APPLICATION_KEY",
        "B2_BUCKET_NAME",
        "B2_ENDPOINT",
        "B2_KEY_ID",
        "B2_PUBLIC_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "B2_REGION=us-west-004",
                "B2_APPLICATION_KEY_ID=standard-key-id",
                "B2_APPLICATION_KEY=application-key",
                "B2_BUCKET_NAME=bucket",
                "B2_ENDPOINT=https://s3.us-west-004.backblazeb2.com",
                "B2_KEY_ID=legacy-key-id",
                "B2_PUBLIC_URL=https://example.com",
            ]
        )
    )

    settings = Settings(_env_file=env_file)

    assert settings.b2_application_key_id == "standard-key-id"
    api_main._validate_startup_configuration(settings)


def test_b2_env_contract_is_shared_with_doctor_and_startup():
    doctor_script = (REPO_ROOT / "scripts/doctor.mjs").read_text()

    assert "b2-env-contract.json" in doctor_script
    assert tuple(B2_ENV_CONTRACT["required"]) == api_main.REQUIRED_B2_ENV_NAMES
    assert api_main.PLACEHOLDER_VALUES == B2_PLACEHOLDER_VALUES


@pytest.mark.parametrize("region", ["us-west-004", "eu-central-003"])
def test_startup_validation_accepts_valid_b2_region(region):
    settings = Settings(
        _env_file=None,
        b2_application_key_id="application-key-id",
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region=region,
    )

    api_main._validate_startup_configuration(settings)


def test_startup_validation_accepts_legacy_b2_key_id(monkeypatch):
    monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
    monkeypatch.setenv("B2_KEY_ID", "legacy-key-id")
    settings = Settings(
        _env_file=None,
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region="us-west-004",
    )

    api_main._validate_startup_configuration(settings)


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

    with pytest.raises(RuntimeError, match="placeholder values"):
        api_main._validate_startup_configuration(settings)


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
def test_startup_validation_rejects_malformed_b2_region(region):
    settings = Settings(
        _env_file=None,
        b2_application_key_id="application-key-id",
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region=region,
    )

    with pytest.raises(RuntimeError, match="Invalid B2_REGION value"):
        api_main._validate_startup_configuration(settings)


def test_startup_validation_does_not_echo_invalid_b2_region():
    sentinel = "sentinel-secret-region-value"
    settings = Settings(
        _env_file=None,
        b2_application_key_id="application-key-id",
        b2_application_key="application-key",
        b2_bucket_name="bucket",
        b2_region=sentinel,
    )

    with pytest.raises(RuntimeError) as exc_info:
        api_main._validate_startup_configuration(settings)

    message = str(exc_info.value)
    assert "B2_REGION" in message
    assert "us-west-004" in message
    assert sentinel not in message


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
