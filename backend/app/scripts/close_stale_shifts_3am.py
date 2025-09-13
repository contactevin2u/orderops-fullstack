# Run with: python -m app.scripts.close_stale_shifts_3am
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db import SessionLocal
from app.models.driver_shift import DriverShift

KL = timezone(timedelta(hours=8))

def next_cutoff_utc(start_utc):
    start_kl = start_utc.astimezone(KL)
    cut_kl = start_kl.replace(hour=3, minute=0, second=0, microsecond=0)
    if start_kl >= cut_kl:
        cut_kl = cut_kl + timedelta(days=1)
    return cut_kl.astimezone(timezone.utc)

def main():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    closed = 0
    try:
        rows = db.execute(
            select(DriverShift).where(DriverShift.clock_out_at.is_(None))
        ).scalars().all()

        for s in rows:
            cutoff = next_cutoff_utc(s.clock_in_at)
            if now >= cutoff:
                s.clock_out_at = cutoff
                s.closure_reason = s.closure_reason or "AUTO_3AM_MIGRATE"
                s.status = "COMPLETED"
                # Calculate working hours
                total_hours = (cutoff - s.clock_in_at).total_seconds() / 3600
                s.total_working_hours = total_hours
                db.add(s)
                closed += 1

        if closed:
            db.commit()
        print(f"[close_stale_shifts_3am] closed={closed}")
    finally:
        db.close()

if __name__ == "__main__":
    main()