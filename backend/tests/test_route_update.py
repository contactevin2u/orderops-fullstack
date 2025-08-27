import sys
from pathlib import Path
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Driver, DriverRoute, Role  # noqa: E402
from app.routers import routes as routes_router  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Driver.__table__.c.id.type = Integer()
    DriverRoute.__table__.c.id.type = Integer()
    DriverRoute.__table__.c.driver_id.type = Integer()
    Base.metadata.create_all(engine, tables=[Driver.__table__, DriverRoute.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_update_route(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    dep = routes_router.router.dependencies[0].dependency
    app.dependency_overrides[dep] = lambda: DummyUser()

    client = TestClient(app)

    with SessionLocal() as db:
        driver = Driver(firebase_uid="u1", name="D1")
        db.add(driver)
        db.flush()
        route = DriverRoute(driver_id=driver.id, route_date=date(2024, 1, 1), name="R1")
        db.add(route)
        db.commit()
        db.refresh(route)

    resp = client.patch(f"/routes/{route.id}", json={"name": "New Name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"

    app.dependency_overrides.clear()
