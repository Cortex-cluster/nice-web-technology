from __future__ import annotations

import uvicorn

from api.app import create_app
from utils.env import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        create_app(),
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
