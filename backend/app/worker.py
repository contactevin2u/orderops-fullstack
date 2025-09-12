import argparse
import logging
import signal
import threading
import time
import traceback
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text, update
from sqlalchemy.orm import Session

from .core.config import settings
from .db import engine
from .models import Job
from .services.ordersvc import create_order_from_parsed
from .services.parser import parse_whatsapp_text
from .services.assignment_service import AssignmentService

logger = logging.getLogger(__name__)

stop_event = threading.Event()
executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="worker-bg")


def _setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _handle_signal(signum, frame):
    logger.info("signal_received signal=%s", signum)
    stop_event.set()


for _sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(_sig, _handle_signal)

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

def retry_db(sess: Session, fn, *args, max_retries: int = 3, backoff: float = 0.5, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # pragma: no cover - broad catch for transient DB failures
            sess.rollback()
            if attempt == max_retries:
                logger.error(
                    "db_operation_failed attempts=%s error=%s", attempt, e
                )
                raise
            sleep = backoff * (2 ** (attempt - 1))
            logger.warning(
                "db_operation_retry attempt=%s error=%s sleep=%.2f",
                attempt,
                e,
                sleep,
            )
            time.sleep(sleep)


def fetch_jobs(sess: Session, limit: int):
    stmt = text(
        """
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
    """
    )
    rows = retry_db(sess, sess.execute, stmt, {"lim": limit}).mappings().all()
    logger.info("fetch_jobs count=%s", len(rows))
    return rows


def process_job_background(job_id: int, kind: str, payload: dict, max_attempts: int):
    """Process job in background thread with fresh session"""
    logger.info("background_start id=%s kind=%s", job_id, kind)
    
    with session_scope() as sess:
        try:
            result = None
            if kind == "PARSE_CREATE":
                text = payload.get("text", "")
                parsed = parse_whatsapp_text(text)
                order = retry_db(sess, create_order_from_parsed, sess, parsed)
                
                # Trigger auto-assignment after order creation (same as API endpoints)
                print(f"🚀 WORKER: Starting auto-assignment for order {order.id} ({order.code})")
                logger.info(f"🚀 WORKER: Starting auto-assignment for order {order.id} ({order.code})")
                try:
                    print(f"🔍 WORKER: Creating assignment service...")
                    assignment_service = AssignmentService(sess)
                    
                    print(f"🔍 WORKER: Calling auto_assign_all() with retry_db...")
                    assignment_result = retry_db(sess, assignment_service.auto_assign_all)
                    
                    print(f"✅ WORKER: Auto-assignment completed for order {order.id}: {assignment_result}")
                    logger.info(f"✅ WORKER: Auto-assignment completed for order {order.id}: {assignment_result}")
                    
                    if assignment_result.get('success'):
                        assigned_count = assignment_result.get('total', 0)
                        print(f"🎯 WORKER: Successfully assigned {assigned_count} orders including {order.id}")
                    else:
                        print(f"⚠️ WORKER: Assignment completed but no orders assigned: {assignment_result}")
                        
                except Exception as e:
                    print(f"❌ WORKER: Auto-assignment FAILED for order {order.id}: {type(e).__name__}: {e}")
                    logger.error(f"❌ WORKER: Auto-assignment FAILED for order {order.id}: {type(e).__name__}: {e}")
                    import traceback
                    print(f"🔥 WORKER: Full traceback: {traceback.format_exc()}")
                    logger.error(f"🔥 WORKER: Full traceback: {traceback.format_exc()}")
                    # Don't fail job if assignment fails
                
                result = {
                    "order_id": order.id,
                    "order_code": order.code,
                    "parsed": parsed,
                }
            elif kind == "AUTO_ASSIGN":
                service = AssignmentService(sess)
                assignment_result = retry_db(sess, service.auto_assign_all)
                result = {
                    "success": assignment_result.get("success", False),
                    "assigned_count": assignment_result.get("total", 0),
                    "message": assignment_result.get("message", ""),
                    "assignments": assignment_result.get("assigned", [])
                }
            else:
                result = {"ok": True}
            
            # Mark job as complete
            retry_db(
                sess,
                sess.execute,
                update(Job)
                .where(Job.id == job_id)
                .values(status="done", result=result, last_error=None),
            )
            
            # Sync result back to background job if needed
            if kind == "PARSE_CREATE" and "background_job_id" in payload:
                background_job_id = payload["background_job_id"]
                try:
                    from .services.background_jobs import job_service
                    job_service.complete_job(sess, background_job_id, result)
                    logger.info("background_sync_success job_id=%s background_job_id=%s", job_id, background_job_id)
                except Exception as e:
                    logger.error("background_sync_failed job_id=%s background_job_id=%s error=%s", job_id, background_job_id, e)
            
            logger.info("background_success id=%s", job_id)
            
        except Exception as e:
            logger.error("background_error id=%s error=%s", job_id, e)
            # Mark as failed
            retry_db(
                sess,
                sess.execute,
                update(Job)
                .where(Job.id == job_id)
                .values(status="error", last_error=f"{e}\n{traceback.format_exc()}"),
            )
            
            # Sync error back to background job if needed
            if kind == "PARSE_CREATE" and "background_job_id" in payload:
                background_job_id = payload["background_job_id"]
                try:
                    from .services.background_jobs import job_service
                    job_service.fail_job(sess, background_job_id, f"Processing failed: {str(e)}")
                    logger.info("background_sync_error job_id=%s background_job_id=%s", job_id, background_job_id)
                except Exception as sync_error:
                    logger.error("background_sync_error_failed job_id=%s background_job_id=%s error=%s", job_id, background_job_id, sync_error)


def process_one(row, sess: Session, max_attempts: int):
    """Non-blocking job dispatcher - immediately dispatches to background thread"""
    jid = row["id"]
    kind = row["kind"]
    payload = row["payload"] or {}
    
    logger.info("process_dispatch id=%s kind=%s attempt=%s", jid, kind, row["attempts"])
    
    # Job is already marked as "running" by fetch_jobs - no additional update needed
    
    # Dispatch to background thread - NON-BLOCKING!
    future = executor.submit(process_job_background, jid, kind, payload, max_attempts)
    logger.info("process_dispatched id=%s", jid)
    
    # Worker immediately continues to next job - no waiting!


def main_loop(batch_size: int, poll_secs: float, max_attempts: int):
    logger.info(
        "worker_loop_start batch_size=%s poll_secs=%.2f max_attempts=%s",
        batch_size,
        poll_secs,
        max_attempts,
    )
    while not stop_event.is_set():
        with session_scope() as s:
            try:
                jobs = fetch_jobs(s, batch_size)
                for j in jobs:
                    process_one(j, s, max_attempts)
            except Exception:  # pragma: no cover - logged for visibility
                logger.exception("worker_iteration_error")
        stop_event.wait(poll_secs)
    logger.info("worker_loop_exit")


def parse_args():
    parser = argparse.ArgumentParser(description="Worker process")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=settings.WORKER_POLL_SECS,
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=settings.WORKER_BATCH_SIZE,
        help="Number of jobs to fetch per batch",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=settings.WORKER_MAX_ATTEMPTS,
        help="Max attempts per job before failing",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _setup_logging()
    args = parse_args()
    logger.info("worker_starting")
    main_loop(args.batch_size, args.poll_interval, args.max_attempts)
