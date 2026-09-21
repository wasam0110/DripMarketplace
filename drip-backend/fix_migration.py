import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect(
        'postgresql://postgres:SyedWasamJaffri@db.xkadscfdvjmaczwkwrfp.supabase.co:6543/postgres'
    )
    await conn.execute("DELETE FROM alembic_version")
    await conn.execute("INSERT INTO alembic_version (version_num) VALUES ('009_create_returns')")
    await conn.close()
    print("Done")

asyncio.run(fix())
