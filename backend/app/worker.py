import time
import traceback
from contextlib import contextmanager
from sqlalchemy import text, update
from sqlalchemy.orm import Session
from .core.config import settings
from .db import engine
from .models import Job
from .services.parser import parse_whatsapp_text
from .services.ordersvc import create_order_from_parsed

@contextmanager
def session_scope():
    if engine is None:
        raise RuntimeError("DATABASE_URL not configured for worker.")
    session = Session(bind=engine, future=True)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def fetch_jobs(sess: Session, limit: int):
    stmt = text("""
        UPDATE jobs
           SET status = 'running', attempts = attempts + 1, updated_at = now()
         WHERE id IN (
            SELECT id FROM jobs
             WHERE status = 'queued'
             ORDER BY id
             FOR UPDATE SKIP LOCKED
             LIMIT :lim
         )
        RETURNING id, kind, payload, attempts
    """)
    rows = sess.execute(stmt, {"lim": limit}).mappings().all()
    return rows

def process_one(row, sess: Session):
    jid = row["id"]; kind = row["kind"]; payload = row["payload"] or {}
    try:
        if kind == "PARSE_CREATE":
            text = payload.get("text","")
            parsed = parse_whatsapp_text(text)
            order = create_order_from_parsed(sess, parsed)
            result = {"order_id": order.id, "order_code": order.code, "parsed": parsed}
        else:
            result = {"ok": True}
        sess.execute(update(Job).where(Job.id==jid).values(status="done", result=result, last_error=None))
    except Exception as e:
        status = "queued" if row["attempts"] < settings.WORKER_MAX_ATTEMPTS else "error"
        sess.execute(update(Job).where(Job.id==jid).values(status=status, last_error=f"{e}\n{traceback.format_exc()}"))

def main_loop():
    while True:
        with session_scope() as s:
            jobs = fetch_jobs(s, settings.WORKER_BATCH_SIZE)
            for j in jobs:
                process_one(j, s)
        time.sleep(settings.WORKER_POLL_SECS)

if __name__ == "__main__":
    print("Worker starting..."); main_loop()
