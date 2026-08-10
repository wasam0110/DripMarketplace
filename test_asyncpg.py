
import asyncio
import asyncpg
from app.core.config import settings

async def main():
    print("Testing direct asyncpg connection...")

    dsn = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )

    conn = await asyncpg.connect(dsn)
    print("ASYNCPG CONNECTION OK")

    await conn.close()

asyncio.run(main())
