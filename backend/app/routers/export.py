from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date, datetime
from io import BytesIO
from openpyxl import Workbook

from ..db import get_session
from ..models import Payment, Order, Customer

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/cash.xlsx")
def cash_export(start: str, end: str, db: Session = Depends(get_session)):
    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except Exception:
        raise HTTPException(400, "Invalid date format (YYYY-MM-DD)")

    rows = (
        db.query(Payment, Order, Customer)
          .join(Order, Order.id == Payment.order_id)
          .join(Customer, Customer.id == Order.customer_id)
          .filter(Payment.status=="POSTED")
          .filter(Payment.date >= start_d, Payment.date <= end_d)
          .order_by(Payment.date.asc(), Payment.id.asc())
          .all()
    )

    wb = Workbook(); ws = wb.active; ws.title = "Payments"
    ws.append(["Date","Order Code","Customer","Amount","Method","Reference","Category"])
    total = 0.0
    for p,o,c in rows:
        ws.append([str(p.date), o.code, c.name, float(p.amount), p.method, p.reference, p.category])
        total += float(p.amount)
    ws.append(["","","TOTAL", total,"","",""])
    bio = BytesIO(); wb.save(bio); bio.seek(0)

    headers = {"Content-Disposition": f'attachment; filename="cash_{start}_{end}.xlsx"'}
    return Response(content=bio.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@router.get("/payments_received.xlsx")
def payments_received_export(start: str, end: str, db: Session = Depends(get_session)):
    """Export posted payments by received date in Excel format.

    This is an alias for :func:`cash_export` but exposes a more descriptive
    endpoint name for consumers looking specifically for payment receipts on a
    cash basis.
    """
    return cash_export(start, end, db)
