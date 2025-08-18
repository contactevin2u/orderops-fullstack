from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..db import get_session
from ..models import Order, Payment
from ..services.documents import invoice_pdf, receipt_pdf, installment_agreement_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/invoice/{order_id}.pdf")
def invoice(order_id: int, db: Session = Depends(get_session)):
    o = db.get(Order, order_id)
    if not o: raise HTTPException(404, "Not found")
    pdf = invoice_pdf(o)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="invoice_{o.code}.pdf"'} )

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
