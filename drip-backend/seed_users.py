import asyncio
import uuid
from argon2 import PasswordHasher

import asyncpg

DB = 'postgresql://postgres:SyedWasamJaffri@db.xkadscfdvjmaczwkwrfp.supabase.co:6543/postgres'

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)

USERS = [
    {'email': 'admin@drip.pk',    'password': 'Admin1234',  'first_name': 'Admin',  'last_name': 'User',   'role': 'admin'},
    {'email': 'customer@drip.pk', 'password': 'Test1234',   'first_name': 'Test',   'last_name': 'Customer','role': 'customer'},
    {'email': 'seller@drip.pk',   'password': 'Test1234',   'first_name': 'Test',   'last_name': 'Seller', 'role': 'seller'},
]

async def seed():
    conn = await asyncpg.connect(DB)
    for u in USERS:
        uid = str(uuid.uuid4())
        hashed = hasher.hash(u['password'])
        await conn.execute('''
            INSERT INTO users (id, email, first_name, last_name, role, password_hash, has_verified_email)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (email) DO NOTHING
        ''', uid, u['email'], u['first_name'], u['last_name'], u['role'], hashed, True)
        print(f"Created: {u['email']} / {u['password']}")
    await conn.close()

asyncio.run(seed())