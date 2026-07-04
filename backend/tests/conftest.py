import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import httpx
import pytest

TEST_BOT_TOKEN = "12345:TEST_TOKEN_FOR_CI"
TEST_USER_ID = 900_000_001

os.environ.setdefault("BOT_TOKEN", TEST_BOT_TOKEN)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://aeon:aeon@localhost:5432/aeon")


def build_init_data(user_id: int = TEST_USER_ID, name: str = "Tester") -> str:
    user = json.dumps({"id": user_id, "first_name": name, "language_code": "ru"})
    data = {"auth_date": str(int(time.time())), "query_id": "AAE", "user": user}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(
        b"WebAppData", os.environ["BOT_TOKEN"].encode(), hashlib.sha256
    ).digest()
    data["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": f"tma {build_init_data()}"}


@pytest.fixture
async def client():
    # Import after env vars are set so Settings picks them up.
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
async def cleanup_test_user():
    yield
    import sqlalchemy as sa

    from app.db.session import engine

    async with engine.begin() as connection:
        await connection.execute(sa.text(f"DELETE FROM users WHERE id = {TEST_USER_ID}"))
