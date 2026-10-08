"""In-memory object store for tests."""

from threading import Lock

from app.repositories.errors import ObjectNotFoundError


class InMemoryObjectStorage:
    """Dict-backed ``ObjectStorage``."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._lock = Lock()
        self.fail_put = False
        self.fail_delete = False
        self.fail_get = False

    async def put(self, key: str, body: bytes, content_type: str) -> None:
        del content_type
        if self.fail_put:
            from app.repositories.errors import StorageError

            raise StorageError
        with self._lock:
            self._objects[key] = body

    async def get(self, key: str) -> bytes:
        if self.fail_get:
            from app.repositories.errors import StorageError

            raise StorageError
        with self._lock:
            body = self._objects.get(key)
        if body is None:
            raise ObjectNotFoundError
        return body

    async def delete(self, key: str) -> None:
        if self.fail_delete:
            from app.repositories.errors import StorageError

            raise StorageError
        with self._lock:
            if key not in self._objects:
                raise ObjectNotFoundError
            del self._objects[key]
