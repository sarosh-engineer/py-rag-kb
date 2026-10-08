"""Opt-in checks against real MongoDB Atlas and S3.

The default suite does not run this module's body. Set RUN_INTEGRATION_TESTS=1
and provide MONGODB_URI, MONGODB_DATABASE, AWS_REGION, AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME in the environment. Failures from
this module must not print those values.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to exercise live MongoDB and S3.",
)


def test_live_mongo_and_s3_accept_connections() -> None:
    import asyncio
    from app.config import Settings
    from app.main import _open_external_stores
    from fastapi import FastAPI

    settings = Settings(app_env="development", jwt_secret_key="k" * 32)
    error = settings.storage_configuration_error()
    if error:
        pytest.fail(error)
    app = FastAPI()
    app.state.settings = settings
    app.state.user_repository = None
    app.state.mongo_client = None
    async def scenario() -> None:
        try:
            await _open_external_stores(app)
        except RuntimeError as exc:
            pytest.fail(str(exc))
        finally:
            client = getattr(app.state, "mongo_client", None)
            if client is not None:
                await client.close()

    asyncio.run(scenario())
