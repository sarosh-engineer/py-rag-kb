"""Object storage contract. Routes do not call boto3."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStorage(Protocol):
    """Bytes stored under a server-generated key."""

    async def put(self, key: str, body: bytes, content_type: str) -> None:
        """Store ``body`` at ``key``."""

    async def get(self, key: str) -> bytes:
        """Return the object bytes."""

    async def delete(self, key: str) -> None:
        """Remove the object. Missing keys raise ``ObjectNotFoundError``."""
