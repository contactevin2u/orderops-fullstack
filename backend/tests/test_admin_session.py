import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, User, AuditLog, Role  # noqa: E402
from app.core.security import hash_password, decode_access_token  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, AuditLog.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_admin_login_persists_24h():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    with SessionLocal() as db:
        admin = User(
            username="boss", password_hash=hash_password("pw"), role=Role.ADMIN
        )
        db.add(admin)
        db.commit()

    resp = client.post("/auth/login", json={"username": "boss", "password": "pw"})
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie")
    assert "max-age=86400" in cookie_header.lower()

    token = resp.cookies.get("token")
    payload = decode_access_token(token)
    expire_dt = datetime.utcfromtimestamp(payload["exp"])
    delta = expire_dt - datetime.utcnow()
    assert 23 * 3600 < delta.total_seconds() <= 24 * 3600

    app.dependency_overrides.clear()
