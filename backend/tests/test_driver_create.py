import sys
from pathlib import Path
import types

from fastapi.testclient import TestClient

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Driver, Role  # noqa: E402
from app.auth.deps import get_current_user  # noqa: E402

from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Driver.__table__.c.id.type = Integer()
    Base.metadata.create_all(engine, tables=[Driver.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_admin_can_create_driver(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    from app.routers import drivers as drv_router

    def fake_create_user(*args, **kwargs):
        return types.SimpleNamespace(uid="u123")

    monkeypatch.setattr(drv_router.firebase_auth, "create_user", fake_create_user, raising=False)
    monkeypatch.setattr(drv_router, "_get_app", lambda: object())

    client = TestClient(app)
    resp = client.post(
        "/drivers",
        json={"email": "d1@example.com", "password": "secret123", "name": "Driver1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Driver1"

    with SessionLocal() as db:
        driver = db.query(Driver).filter_by(firebase_uid="u123").one()
        assert driver.name == "Driver1"

    app.dependency_overrides.clear()
