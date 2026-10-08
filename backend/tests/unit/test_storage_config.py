"""Storage configuration failures do not echo secrets."""

import pytest

from app.config import Settings
from app.logging_config import redact_text
from app.main import create_app


def test_missing_storage_settings_name_variables_only() -> None:
    secret_uri = "mongodb+srv://example-user:example-pass@cluster.example/db"
    with pytest.raises(RuntimeError) as captured:
        create_app(
            Settings(
                app_env="local",
                jwt_secret_key="k" * 32,
                mongodb_uri=secret_uri,
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="example-secret-value",
            )
        )

    message = str(captured.value)
    assert "AWS_REGION" in message
    assert "S3_BUCKET_NAME" in message
    assert "example-pass" not in message
    assert "example-secret-value" not in message
    assert "AKIAIOSFODNN7EXAMPLE" not in message


def test_invalid_mongodb_scheme_does_not_echo_the_value() -> None:
    with pytest.raises(RuntimeError) as captured:
        create_app(
            Settings(
                app_env="local",
                jwt_secret_key="k" * 32,
                mongodb_uri="http://user:example-pass@localhost",
                mongodb_database="genai_rag",
                aws_region="ap-south-1",
                aws_access_key_id="example-key",
                aws_secret_access_key="example-secret",
                s3_bucket_name="documents",
            )
        )

    assert str(captured.value) == "MONGODB_URI is invalid."
    assert "example-pass" not in str(captured.value)


def test_log_redaction_removes_a_mongodb_uri() -> None:
    redacted = redact_text("connect mongodb+srv://user:example-pass@cluster.example/db now")

    assert "example-pass" not in redacted
    assert "[REDACTED]" in redacted
