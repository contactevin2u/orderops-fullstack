import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Driver, DriverDevice  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlalchemy import Integer

    Driver.__table__.c.id.type = Integer()
    DriverDevice.__table__.c.id.type = Integer()
    DriverDevice.__table__.c.driver_id.type = Integer()
    Base.metadata.create_all(engine, tables=[Driver.__table__, DriverDevice.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_device_register(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    from app.auth import firebase as fb

    def fake_verify(token):
        assert token == "good"
        return {"uid": "u1", "phone_number": "+123", "name": "D1"}

    monkeypatch.setattr(fb, "verify_firebase_id_token", fake_verify)

    client = TestClient(app)

    resp = client.post(
        "/drivers/devices",
        json={"token": "tok", "platform": "android", "app_version": "1.0", "model": "Pixel"},
        headers={"Authorization": "Bearer good"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    with SessionLocal() as db:
        drivers = db.query(Driver).all()
        assert len(drivers) == 1
        assert drivers[0].firebase_uid == "u1"
        devices = db.query(DriverDevice).all()
        assert len(devices) == 1
        assert devices[0].driver_id == drivers[0].id
        assert devices[0].token == "tok"

    app.dependency_overrides.clear()
