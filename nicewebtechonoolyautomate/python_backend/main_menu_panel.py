from __future__ import annotations

import os

from dotenv import load_dotenv
import uvicorn

from menu_panel import create_app


def load_panel_environment() -> None:
    load_dotenv(".env", override=False)
    load_dotenv(".env.menu-panel", override=True)


def main() -> None:
    load_panel_environment()
    host = os.getenv("MENU_PANEL_FASTAPI_HOST", "127.0.0.1")
    port = int(os.getenv("MENU_PANEL_FASTAPI_PORT", "8001"))
    uvicorn.run(
        create_app(),
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
