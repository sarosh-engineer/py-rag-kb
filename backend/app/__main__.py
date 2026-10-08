"""Start the API with the configured bind address.

The container image does not use this module. Its command line passes
``--host 0.0.0.0`` so the local default of ``127.0.0.1`` cannot make the
container unreachable.
"""

import uvicorn

from app.config import Settings, load_settings


def server_options(settings: Settings) -> dict[str, object]:
    """Uvicorn keyword arguments for a local or VM process."""
    return {
        "app": "app.main:app",
        "host": settings.host,
        "port": settings.port,
        "access_log": False,
    }


def main() -> None:
    uvicorn.run(**server_options(load_settings()))


if __name__ == "__main__":
    main()
