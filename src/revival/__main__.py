from __future__ import annotations

import uvicorn

from revival.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "revival.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
