"""
app/core/database.py
────────────────────
Async SQLAlchemy 2.x engine, session factory, and dependency.

Connection lifecycle:
  • Engine created once at startup (lifespan).
  • Sessions are created per-request via get_db() dependency.
  • Sessions auto-rollback on exception, auto-close on response completion.
  • SELECT FOR UPDATE used for inventory operations (see order_service.py).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Module-level singletons (set in create_engine_and_session) ────────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Create the async engine and session factory.
    Called once during application lifespan startup.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,        # Discard stale connections
        pool_recycle=3600,         # Recycle connections after 1 hour
        echo=settings.is_development,  # Log SQL in dev only
        json_serializer=_json_serializer,
        json_deserializer=_json_deserializer,
        connect_args={
            "server_settings": {
                "application_name": f"drip-api-{settings.ENVIRONMENT}",
                "jit": "off",       # Disable JIT for short queries
            },
            "command_timeout": 30,
        },
    )

    # Log pool events in development
    if settings.is_development:
        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_conn: Any, connection_record: Any) -> None:
            logger.debug("database.pool.connect")

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,     # Don't lazy-load after commit
        autocommit=False,
        autoflush=False,
    )

    return engine, session_factory


async def init_db() -> None:
    """Called at app startup. Creates engine and verifies connectivity."""
    global _engine, _session_factory
    _engine, _session_factory = create_engine_and_session()

    # Verify connection
    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database.connected", pool_size=settings.DATABASE_POOL_SIZE)
    except Exception as exc:
        logger.error("database.connection_failed", error=str(exc))
        raise


async def close_db() -> None:
    """Called at app shutdown. Disposes the connection pool."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("database.disconnected")
        _engine = None


# ── Request-scoped session dependency ─────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...

    Behaviour:
        • Yields a session with an open transaction.
        • On success: transaction is committed by the route handler or service.
        • On exception: rolls back automatically.
        • Always closes the session on completion.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Utility: run in transaction ────────────────────────────────────────────────

async def atomic(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for explicit transaction control within a service.
    Use when you need fine-grained commit/rollback control.

    Usage:
        async with atomic(session):
            await repo.create(session, ...)
            await inventory_repo.decrement(session, ...)
    """
    async with session.begin():
        yield session


# ── Serialisers ───────────────────────────────────────────────────────────────

def _json_serializer(obj: Any) -> str:
    import orjson
    return orjson.dumps(obj).decode()


def _json_deserializer(obj: str) -> Any:
    import orjson
    return orjson.loads(obj)