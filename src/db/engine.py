import os
import stat
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event, inspect, text

from src.db.tables import Base
from src.security import crypto

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _set_wal_mode(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def _restrict_permissions(db_path: str) -> None:
    """Make the cache file owner-only where the OS lets us say so.

    On Windows the file inherits the user profile ACL, which already excludes
    other non-administrator users; there is no portable chmod equivalent worth
    faking here.
    """
    if sys.platform == "win32":
        return
    path = Path(db_path)
    for candidate in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")):
        if candidate.exists():
            try:
                os.chmod(candidate, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass


async def init_db(db_path: str, *, encryption: bool = True) -> None:
    global _engine, _session_factory
    if _engine is not None:
        return

    crypto.configure(enabled=encryption)
    if encryption:
        # Resolve the key now so a missing credential store fails here, with a
        # message naming the fix, rather than midway through a cache write.
        crypto.load_or_create_key()

    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    event.listen(_engine.sync_engine, "connect", _set_wal_mode)

    # Migrate: drop stale cache tables — cache rebuilds automatically
    async with _engine.begin() as conn:
        def _migrate_cache_tables(connection):
            insp = inspect(connection)
            # Drop old "cached_entities" (renamed to "cached_entity")
            if insp.has_table("cached_entities"):
                connection.execute(text("DROP TABLE cached_entities"))
            # Drop tables with old budget_id column
            for table in ("cached_entity", "server_knowledge"):
                if insp.has_table(table):
                    columns = [c["name"] for c in insp.get_columns(table)]
                    if "budget_id" in columns:
                        connection.execute(text(f"DROP TABLE {table}"))
            # Drop payload tables still holding a plaintext JSON/TEXT `data`
            # column. It is now a BLOB carrying an encryption envelope, and the
            # two formats cannot be read interchangeably.
            for table in ("cached_entity", "response_cache"):
                if not insp.has_table(table):
                    continue
                data_column = next(
                    (c for c in insp.get_columns(table) if c["name"] == "data"), None
                )
                if data_column is None or "BLOB" in str(data_column["type"]).upper():
                    continue
                connection.execute(text(f"DROP TABLE {table}"))
                # Emptying cached_entity without resetting server_knowledge would
                # leave delta sync believing it is current, so the next sync would
                # fetch only changes since then and the entities dropped here would
                # never come back. Reset the knowledge with it.
                if table == "cached_entity" and insp.has_table("server_knowledge"):
                    connection.execute(text("DROP TABLE server_knowledge"))

        await conn.run_sync(_migrate_cache_tables)
        await conn.run_sync(Base.metadata.create_all)

    _restrict_permissions(db_path)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


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
