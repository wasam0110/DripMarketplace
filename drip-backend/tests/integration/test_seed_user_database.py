"""Bootstrap account helper against the disposable database schema."""
import pytest
from argon2 import PasswordHasher

from app.schemas.auth import RegisterRequest
from seed_users import insert_user

pytestmark = pytest.mark.integration


async def test_bootstrap_account_never_overwrites_existing_credentials_or_role(db):
    connection = await db.connection()
    raw = await connection.get_raw_connection()
    driver = raw.driver_connection
    customer = RegisterRequest(email='bootstrap@example.com', first_name='Test', last_name='User', password='ValidTestPassword123')
    first = await insert_user(driver, customer, 'customer', True)
    assert first is not None
    replacement = customer.model_copy(update={'password': 'AnotherTestPassword456'})
    assert await insert_user(driver, replacement, 'admin', True) is None
    row = await driver.fetchrow('SELECT role, password_hash, has_verified_email FROM users WHERE id=$1', first)
    assert row['role'] == 'customer'
    assert row['has_verified_email'] is True
    assert PasswordHasher().verify(row['password_hash'], customer.password)
    assert row['password_hash'] != customer.password
    with pytest.raises(ValueError):
        await insert_user(driver, customer, 'seller', True)
