import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, User, AuditLog, Role  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, AuditLog.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_register_requires_admin_for_subsequent_users():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    # first user becomes admin without auth
    resp = client.post("/auth/register", json={"username": "boss", "password": "pw"})
    assert resp.status_code == 200
    assert resp.json()["role"] == Role.ADMIN.value

    # unauthenticated second registration is rejected
    resp = client.post("/auth/register", json={"username": "bob", "password": "pw"})
    assert resp.status_code == 401

    # login as admin
    resp = client.post("/auth/login", json={"username": "boss", "password": "pw"})
    assert resp.status_code == 200
    token = resp.cookies.get("token")
    # admin creates another user (defaults to cashier)
    resp = client.post(
        "/auth/register",
        json={"username": "cashier", "password": "pw"},
        cookies={"token": token},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == Role.CASHIER.value

    # cashier cannot register new user
    resp = client.post("/auth/login", json={"username": "cashier", "password": "pw"})
    cashier_token = resp.cookies.get("token")
    resp = client.post(
        "/auth/register",
        json={"username": "third", "password": "pw"},
        cookies={"token": cashier_token},
    )
    assert resp.status_code == 403

    app.dependency_overrides.clear()
