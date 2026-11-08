import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

# Settings must be in the environment before the app is imported.
os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://riskwise_app:app@localhost:5432/riskwise_test")
os.environ["AUTH_MODE"] = "dev"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JOB_TOKEN"] = "test-job-token"
os.environ["STORAGE_LOCAL_DIR"] = tempfile.mkdtemp(prefix="riskwise-test-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.db import get_engine  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean():
    yield
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "TRUNCATE audit_log, findings, analysis_runs, clauses, contracts, policy_rules, org_settings, "
                "memberships, users, organizations CASCADE"
            )
        )


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def token_for(client: TestClient, email: str) -> dict:
    r = client.post("/api/v1/dev/token", json={"email": email})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def demo_contract() -> bytes:
    return (FIXTURES / "cloudstack.txt").read_bytes()
