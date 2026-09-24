"""Inspect or apply Alembic migrations without overwriting the version table."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Show current revision (the default)")
    action.add_argument("--upgrade", action="store_true", help="Apply pending migrations to head")
    parser.add_argument("--sql", action="store_true", help="With --upgrade, print SQL without applying it")
    args = parser.parse_args(argv)
    if args.sql and not args.upgrade:
        parser.error("--sql requires --upgrade")
    load_dotenv(ROOT / ".env", override=False)
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+asyncpg://"):
        parser.error("Set DATABASE_URL using postgresql+asyncpg:// in your environment or local .env")
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    try:
        if args.upgrade:
            command.upgrade(config, "head", sql=args.sql)
        else:
            command.current(config, verbose=True)
    except Exception:
        print("Migration command failed. Check database access and migration history; no revision was forcibly stamped.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
