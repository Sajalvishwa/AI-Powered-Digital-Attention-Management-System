"""Integration tests: real FastAPI app + real PostgreSQL *test* database.

Safety rules built in:
  * only a database whose name ends with "_test" is ever used
  * the dev database (attention_dev) is never touched
URL comes from TEST_DATABASE_URL (env or root .env). If missing, it is derived
from DATABASE_URL in the root .env by replacing the trailing "_dev" with "_test".
"""
import pathlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

ROOT_ENV = pathlib.Path(__file__).resolve().parents[3] / ".env"


def _read_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _test_db_url() -> str | None:
    import os

    env = _read_env_file(ROOT_ENV)
    url = os.environ.get("TEST_DATABASE_URL") or env.get("TEST_DATABASE_URL")
    if url:
        return url
    dev = env.get("DATABASE_URL")  # read from file: tests/conftest.py sets a dummy env var
    if dev:
        parsed = make_url(dev)
        if parsed.database and parsed.database.endswith("_dev"):
            parsed = parsed.set(database=parsed.database[: -len("_dev")] + "_test")
            return parsed.render_as_string(hide_password=False)
    return None


@pytest.fixture(scope="session")
def engine():
    url = _test_db_url()
    if not url:
        pytest.skip("No test database configured (add TEST_DATABASE_URL to .env)")
    db_name = make_url(url).database or ""
    if not db_name.endswith("_test"):
        pytest.skip(f"Refusing to run: database '{db_name}' does not end with _test")

    eng = create_engine(url, pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"Cannot connect to test database '{db_name}': {type(exc).__name__}. "
            "Create it in pgAdmin: CREATE DATABASE attention_test OWNER attention;"
        )

    from app.core.database import Base
    import app.models  # noqa: F401  (registers all tables)

    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
    Base.metadata.drop_all(eng)  # always start from the current models
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def client(engine):
    from fastapi.testclient import TestClient

    from app.core import rate_limit
    from app.core.database import get_db
    from app.main import app

    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with engine.begin() as conn:  # clean slate for every test
        conn.execute(text("TRUNCATE TABLE users CASCADE"))
    rate_limit.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def signup(client):
    """signup('x@example.com') -> {'access', 'refresh', 'headers'}"""

    def _signup(email: str, name: str = "Test User", password: str = "Strong123") -> dict:
        r = client.post(
            "/api/v1/auth/register", json={"name": name, "email": email, "password": password}
        )
        assert r.status_code == 201, r.text
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        tokens = r.json()
        return {
            "access": tokens["access_token"],
            "refresh": tokens["refresh_token"],
            "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
        }

    return _signup


@pytest.fixture()
def user_a(signup):
    return signup("a@example.com", "User A")["headers"]


@pytest.fixture()
def user_b(signup):
    return signup("b@example.com", "User B")["headers"]


@pytest.fixture()
def make_session():
    """make_session(minutes_ago=10, seconds=60, app_name='Code.exe', **overrides) -> dict"""

    def _make(minutes_ago: int = 10, seconds: int = 60, app_name: str = "Code.exe", **over):
        end = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        start = end - timedelta(seconds=seconds)
        data = {
            "client_id": str(uuid.uuid4()),
            "app_name": app_name,
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
        }
        data.update(over)
        return data

    return _make
