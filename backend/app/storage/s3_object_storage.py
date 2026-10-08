"""S3 implementation of ``ObjectStorage``.

boto3 is synchronous. Calls run in a worker thread so the event loop stays
free. Error logs keep the S3 error code and omit the exception text.
"""

import asyncio
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.config import Settings
from app.repositories.errors import ObjectNotFoundError, StorageError

logger = logging.getLogger("app.storage.s3")

_MISSING = {"NoSuchKey", "404", "NotFound"}


class S3ObjectStorage:
    """Store document bytes in one configured bucket."""

    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> "S3ObjectStorage":
        client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        return cls(client, settings.s3_bucket_name)

    def check(self) -> None:
        """Confirm the bucket is reachable. Called during startup."""
        self._call(self._client.head_bucket, Bucket=self._bucket)

    async def put(self, key: str, body: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._call,
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._read, key)

    def _read(self, key: str) -> bytes:
        response = self._call(self._client.get_object, Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            self._call,
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )

    def _call(self, operation: Any, **kwargs: Any) -> Any:
        try:
            return operation(**kwargs)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", "unknown"))
            logger.info("object storage error", extra={"exception_type": code})
            if code in _MISSING:
                raise ObjectNotFoundError from None
            raise StorageError from None
