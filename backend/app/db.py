import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def _coerce_psycopg(url: str) -> str:
    # Force SQLAlchemy to use psycopg v3 driver
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

def _append_sslmode(url: str) -> str:
    if url and "postgres" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}sslmode=require"
    return url

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    DATABASE_URL = _coerce_psycopg(DATABASE_URL)
    DATABASE_URL = _append_sslmode(DATABASE_URL)

engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True) if engine else None

def get_session():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured for this environment.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
