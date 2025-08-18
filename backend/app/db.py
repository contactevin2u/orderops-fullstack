import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def _append_sslmode(url: str) -> str:
    if url and "postgres" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}sslmode=require"
    return url

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_URL = _append_sslmode(DATABASE_URL) if DATABASE_URL else ""

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
