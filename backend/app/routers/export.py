from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import date, datetime
from io import BytesIO
from openpyxl import Workbook
import uuid
from pydantic import BaseModel

from ..db import get_session
from ..models import Payment, Order, Customer

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/cash.xlsx")
def cash_export(start: str, end: str, mark: bool = False, db: Session = Depends(get_session)):
    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except Exception:
        raise HTTPException(400, "Invalid date format (YYYY-MM-DD)")

    q = (
        db.query(Payment, Order, Customer)
        .join(Order, Order.id == Payment.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .filter(Payment.status == "POSTED")
        .filter(Payment.date >= start_d, Payment.date <= end_d)
        .order_by(Payment.date.asc(), Payment.id.asc())
    )
    if mark:
        q = q.filter(Payment.exported_at.is_(None))
    rows = q.all()

    wb = Workbook(); ws = wb.active; ws.title = "Payments"
    ws.append(["Date","Order Code","Customer","Amount","Method","Reference","Category"])
    total = 0.0
    exported_ids: list[int] = []
    for p,o,c in rows:
        ws.append([str(p.date), o.code, c.name, float(p.amount), p.method, p.reference, p.category])
        total += float(p.amount)
        exported_ids.append(p.id)
    ws.append(["","","TOTAL", total,"","",""])
    bio = BytesIO(); wb.save(bio); bio.seek(0)

    if mark and exported_ids:
        run_id = str(uuid.uuid4())
        now = datetime.utcnow()
        db.query(Payment).filter(Payment.id.in_(exported_ids)).update(
            {"export_run_id": run_id, "exported_at": now}, synchronize_session=False
        )
        db.commit()

    headers = {"Content-Disposition": f'attachment; filename="cash_{start}_{end}.xlsx"'}
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/payments_received.xlsx")
def payments_received_export(start: str, end: str, db: Session = Depends(get_session)):
    """Export posted payments by received date in Excel format.

    This is an alias for :func:`cash_export` but exposes a more descriptive
    endpoint name for consumers looking specifically for payment receipts on a
    cash basis.
    """
    return cash_export(start, end, db=db)


class CashExportIn(BaseModel):
    start: str
    end: str
    mark: bool = False


@router.post("/cash")
def cash_export_json(body: CashExportIn, db: Session = Depends(get_session)):
    """Preview posted payments within a date range in JSON format.

    When ``mark`` is true, behaves like ``/export/cash.xlsx`` by stamping
    ``export_run_id``/``exported_at`` so they are excluded from future runs.
    """
    try:
        start_d = date.fromisoformat(body.start)
        end_d = date.fromisoformat(body.end)
    except Exception:
        raise HTTPException(400, "Invalid date format (YYYY-MM-DD)")

    q = (
        db.query(Payment, Order, Customer)
        .join(Order, Order.id == Payment.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .filter(Payment.status == "POSTED")
        .filter(Payment.date >= start_d, Payment.date <= end_d)
        .order_by(Payment.date.asc(), Payment.id.asc())
    )
    if body.mark:
        q = q.filter(Payment.exported_at.is_(None))
    rows = q.all()

    total = 0.0
    exported_ids: list[int] = []
    out: list[dict] = []
    for p, o, c in rows:
        total += float(p.amount)
        exported_ids.append(p.id)
        out.append(
            {
                "id": p.id,
                "date": str(p.date),
                "order_id": p.order_id,
                "order_code": o.code,
                "customer_name": c.name,
                "amount": float(p.amount),
                "method": p.method,
                "reference": p.reference,
                "category": p.category,
            }
        )

    if body.mark and exported_ids:
        run_id = str(uuid.uuid4())
        now = datetime.utcnow()
        db.query(Payment).filter(Payment.id.in_(exported_ids)).update(
            {"export_run_id": run_id, "exported_at": now}, synchronize_session=False
        )
        db.commit()

    return {"items": out, "total": total}


@router.get("/runs")
def list_runs(db: Session = Depends(get_session)):
    rows = (
        db.query(
            Payment.export_run_id.label("run_id"),
            func.min(Payment.exported_at).label("created_at"),
            func.count(Payment.id).label("count"),
            func.sum(Payment.amount).label("sum_amount"),
        )
        .filter(Payment.export_run_id.isnot(None))
        .group_by(Payment.export_run_id)
        .order_by(func.min(Payment.exported_at).desc())
        .all()
    )
    out = [
        {
            "run_id": run_id,
            "created_at": created_at,
            "count": count,
            "sum_amount": float(sum_amount or 0),
        }
        for run_id, created_at, count, sum_amount in rows
    ]
    return out


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_session)):
    rows = (
        db.query(Payment, Order, Customer)
        .join(Order, Order.id == Payment.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .filter(Payment.export_run_id == run_id)
        .order_by(Payment.date.asc(), Payment.id.asc())
        .all()
    )
    out = [
        {
            "id": p.id,
            "date": str(p.date),
            "order_id": p.order_id,
            "order_code": o.code,
            "customer_name": c.name,
            "amount": float(p.amount),
            "method": p.method,
            "reference": p.reference,
            "category": p.category,
        }
        for p, o, c in rows
    ]
    return out


@router.post("/runs/{run_id}/rollback")
def rollback_run(run_id: str, db: Session = Depends(get_session)):
    updated = (
        db.query(Payment)
        .filter(Payment.export_run_id == run_id)
        .update({"export_run_id": None, "exported_at": None}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}
