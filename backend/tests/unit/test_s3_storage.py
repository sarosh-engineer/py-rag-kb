"""S3 storage service with a fake boto3 client."""

import asyncio

import pytest
from botocore.exceptions import ClientError

from app.repositories.errors import ObjectNotFoundError, StorageError
from app.storage.s3_object_storage import S3ObjectStorage


class _Body:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail: str | None = None

    def head_bucket(self, Bucket: str) -> dict:
        del Bucket
        if self.fail == "head":
            raise ClientError({"Error": {"Code": "403"}}, "HeadBucket")
        return {}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> dict:
        del Bucket, ContentType
        if self.fail == "put":
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        self.objects[Key] = Body
        return {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        del Bucket
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": _Body(self.objects[Key])}

    def delete_object(self, Bucket: str, Key: str) -> dict:
        del Bucket
        if self.fail == "delete":
            raise ClientError({"Error": {"Code": "InternalError"}}, "DeleteObject")
        self.objects.pop(Key, None)
        return {}


def test_put_get_and_delete_round_trip() -> None:
    client = FakeS3Client()
    storage = S3ObjectStorage(client, "documents-bucket")

    async def scenario() -> None:
        await storage.put("documents/abc/notes.txt", b"hello", "text/plain")
        assert await storage.get("documents/abc/notes.txt") == b"hello"
        await storage.delete("documents/abc/notes.txt")
        with pytest.raises(ObjectNotFoundError):
            await storage.get("documents/abc/notes.txt")

    asyncio.run(scenario())


def test_upload_and_delete_failures_hide_driver_details() -> None:
    client = FakeS3Client()
    storage = S3ObjectStorage(client, "documents-bucket")

    async def scenario():
        client.fail = "put"
        with pytest.raises(StorageError) as put_error:
            await storage.put("documents/abc/notes.txt", b"hello", "text/plain")
        client.fail = "delete"
        client.objects["documents/abc/notes.txt"] = b"hello"
        with pytest.raises(StorageError) as delete_error:
            await storage.delete("documents/abc/notes.txt")
        return put_error, delete_error

    put_error, delete_error = asyncio.run(scenario())

    assert "AccessDenied" not in str(put_error.value)
    assert "InternalError" not in str(delete_error.value)
    assert client.objects["documents/abc/notes.txt"] == b"hello"
