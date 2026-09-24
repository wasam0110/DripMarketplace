"""Create one explicitly configured bootstrap account without default credentials."""
from __future__ import annotations

import argparse
import asyncio
import getpass
import os
from pathlib import Path
import sys
from uuid import uuid4

import asyncpg
from argon2 import PasswordHasher
from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest

ROOT = Path(__file__).resolve().parent


async def insert_user(connection, user: RegisterRequest, role: str, verified: bool):
    """Insert a new account; never change an existing account's password or role."""
    if role not in {"admin", "customer"}:
        raise ValueError("Use seller registration to create a complete seller profile")
    password_hash = PasswordHasher(
        time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16,
    ).hash(user.password)
    return await connection.fetchval(
        """INSERT INTO users
           (id, email, first_name, last_name, role, password_hash, has_verified_email)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           ON CONFLICT (email) DO NOTHING RETURNING id""",
        uuid4(), user.email, user.first_name, user.last_name, role, password_hash, verified,
    )


async def seed(database_url: str, user: RegisterRequest, role: str, verified: bool):
    connection = await asyncpg.connect(database_url, timeout=15)
    try:
        async with connection.transaction():
            return await insert_user(connection, user, role, verified)
    finally:
        await connection.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", default="Admin")
    parser.add_argument("--last-name", default="User")
    parser.add_argument("--role", choices=["admin", "customer"], default="admin")
    parser.add_argument("--verified", action="store_true", help="Mark an email you control as verified")
    parser.add_argument("--password-stdin", action="store_true", help="Read one password line from stdin instead of prompting")
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env", override=False)
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgresql+asyncpg://", "postgresql://", "postgres://")):
        parser.error("Set DATABASE_URL in your environment or local .env first")
    url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("New account password: ")
        if password != getpass.getpass("Confirm password: "):
            parser.error("Passwords did not match")
    try:
        user = RegisterRequest(email=args.email, first_name=args.first_name,
                               last_name=args.last_name, password=password)
    except ValidationError:
        parser.error("Invalid email/name or password. Password needs 8–128 characters, upper/lowercase letters and a digit")
    try:
        created_id = asyncio.run(seed(url, user, args.role, args.verified))
    except Exception:
        print("Account creation failed. Check database access and apply migrations first. Credentials were not printed.", file=sys.stderr)
        return 1
    print("Account created." if created_id else "Account already exists; no changes made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
