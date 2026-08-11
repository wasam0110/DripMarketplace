"""
alembic/env.py
──────────────
Alembic migration environment configured for async SQLAlchemy.

How to use:
  alembic revision --autogenerate -m "description"
  alembic upgrade head
  alembic downgrade -1
  alembic current
  alembic history
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# ── Load all models so Alembic can detect schema changes ─────────────────────
# Import Base first, then every model module. Add new model files here.
from app.models.base import Base  # noqa: F401
# from app.models.user import User  # noqa: F401  (uncomment as blocks are built)
# from app.models.seller import Seller  # noqa: F401
# from app.models.product import Product  # noqa: F401
# from app.models.order import Order  # noqa: F401
# from app.models.wallet import SellerWallet  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Read logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our model metadata for --autogenerate
target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return url  # keep asyncpg:// — async_engine_from_config needs it


def get_sync_url() -> str:
    return get_url().replace("postgresql+asyncpg://", "postgresql+psycopg2://")

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without a live connection.
    Useful for reviewing migrations before applying.

    Usage: alembic upgrade head --sql > migration.sql
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Include all schemas
        include_schemas=True,
        # Render item type for PostgreSQL-specific types
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,    # No pooling for migration runs
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — applies changes to a live database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()