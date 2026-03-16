from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

from src.db.tables import Base

_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


def _set_wal_mode(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


async def init_db(db_path: str) -> None:
    global _engine, _session_factory
    if _engine is not None:
        return

    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    event.listen(_engine.sync_engine, "connect", _set_wal_mode)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def get_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory()


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
