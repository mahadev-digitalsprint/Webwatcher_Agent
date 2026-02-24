from webwatcher.core.database import get_engine
from webwatcher.db.models import Base


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

