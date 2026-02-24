import asyncio

from webwatcher.db.init_db import init_db


def bootstrap() -> None:
    asyncio.run(init_db())


if __name__ == "__main__":
    bootstrap()

