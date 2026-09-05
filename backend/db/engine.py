"""
SIH26056 — Database engine and session management.

PostgreSQL is the target store and what ``docker-compose`` provisions. SQLite is
supported so the project runs on a machine with no database server.

There is deliberately no in-memory mode. Published figures must survive a restart, so
the storage layer is never optional.

Connection failures are raised, not swallowed. A silent fallback to a different store
would mean published values quietly stop being the ones that were published.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import DatabaseSettings, get_settings
from db.models import Base


class Database:
    """Owns the async engine and session factory for one database URL."""

    def __init__(self, settings: Optional[DatabaseSettings] = None):
        self.settings = settings or get_settings().database
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    # ── lifecycle ──

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> AsyncEngine:
        url = self.settings.url
        kwargs: dict = {"echo": self.settings.echo, "future": True}

        if url.startswith("sqlite"):
            # SQLite needs no pooling configuration, and check_same_thread must be
            # relaxed for the async driver.
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 60.0}
        else:
            kwargs.update(
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                # Verify a pooled connection before use; long-idle Postgres
                # connections are otherwise handed out already dead.
                pool_pre_ping=True,
            )

        logger.info(
            f"Database engine: "
            f"{'PostgreSQL' if self.settings.is_postgres else 'SQLite'} "
            f"({_redact_url(url)})"
        )
        engine = create_async_engine(url, **kwargs)
        if url.startswith("sqlite"):
            from sqlalchemy import event

            @event.listens_for(engine.sync_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                try:
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA busy_timeout=60000")
                finally:
                    cursor.close()

        return engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    async def create_schema(self) -> None:
        """
        Create tables that do not exist yet.

        Used only by isolated tests and explicitly configured throwaway local stores.
        Shared or production stores must be created/updated by Alembic, so that schema
        state is versioned rather than inferred from the currently running code.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Schema ensured: {len(Base.metadata.tables)} table(s)")

    async def require_migration_revision(self, expected_revision: str) -> None:
        """Fail startup unless Alembic has applied the schema expected by this API.

        This intentionally refuses an unversioned/legacy database. Treating a
        pre-existing schema as compatible merely because some tables have familiar
        names is what caused the former Docker bootstrap conflict.
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                revisions = [str(value) for value in result.scalars().all()]
        except SQLAlchemyError as exc:
            raise RuntimeError(
                "Database schema is not Alembic-managed. Run `alembic upgrade head` "
                "against a clean database; do not point this build at the legacy "
                "database without a reviewed migration."
            ) from exc

        if revisions != [expected_revision]:
            raise RuntimeError(
                "Database schema revision does not match this API "
                f"(found {revisions or 'none'}, expected {expected_revision!r}). "
                "Run `alembic upgrade head` before starting the API."
            )

    async def drop_schema(self) -> None:
        """Drop all tables. Used by tests only."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def healthcheck(self) -> tuple[bool, Optional[str]]:
        """
        Verify the database is reachable.

        Returns ``(ok, error)`` rather than raising so the health endpoint can report
        a degraded database without the whole API failing.
        """
        from sqlalchemy import text

        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, None
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")

    # ── sessions ──

    def session(self) -> AsyncSession:
        """A new session. The caller owns commit/rollback."""
        return self.session_factory()

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        """
        Transactional scope: commits on success, rolls back on exception.

        Rolling back rather than partially committing matters here — a half-written
        collection run would leave observations with no run to attribute them to.
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def _redact_url(url: str) -> str:
    """Strip credentials before logging a connection URL."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    _, _, host_part = rest.rpartition("@")
    return f"{scheme}://***@{host_part}"


# ── module-level instance, used by the API ──

_database: Optional[Database] = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
    return _database


def set_database(database: Optional[Database]) -> None:
    """Override the module-level instance. Used by tests to point at a temp database."""
    global _database
    _database = database


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session."""
    db = get_database()
    async with db.session_factory() as session:
        yield session
