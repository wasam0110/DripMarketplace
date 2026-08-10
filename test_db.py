import asyncio
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    print("Testing database connection...")
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.connect():
            print("DATABASE CONNECTION OK")
    finally:
        await engine.dispose()

asyncio.run(main())
