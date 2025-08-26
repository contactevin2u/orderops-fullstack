from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..db import get_session
from ..models import Order, Payment, Role
from ..services.documents import receipt_pdf, installment_agreement_pdf
from ..auth.deps import require_roles

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)

@router.get("/receipt/{payment_id}.pdf")
def receipt(payment_id: int, db: Session = Depends(get_session)):
    p = db.get(Payment, payment_id)
    if not p: raise HTTPException(404, "Not found")
    o = db.get(Order, p.order_id)
    pdf = receipt_pdf(o,p)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="receipt_{o.code}_{p.id}.pdf"'} )

@router.get("/installment-agreement/{order_id}.pdf")
def installment(order_id: int, db: Session = Depends(get_session)):
    o = db.get(Order, order_id)
    if not o: raise HTTPException(404, "Not found")
    if not o.plan or o.plan.plan_type != "INSTALLMENT":
        raise HTTPException(400, "No installment plan")
    pdf = installment_agreement_pdf(o, o.plan)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="instalment_{o.code}.pdf"'} )
