from datetime import datetime, date
from sqlalchemy.orm import Session
from ..models import Customer, Order, OrderItem, Plan, Payment
from ..utils.codegen import generate_order_code
from decimal import Decimal

def _d(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))

def create_order_from_parsed(db: Session, parsed: dict) -> Order:
    pdata = parsed["customer"]
    odata = parsed["order"]

    # customer upsert by phone if available
    customer = None
    phone = (pdata.get("phone") or "").strip()
    if phone:
        customer = db.query(Customer).filter(Customer.phone == phone).first()
    if not customer:
        customer = Customer(name=pdata.get("name") or "Customer", phone=phone, address=pdata.get("address"), map_url=pdata.get("map_url"))
        db.add(customer); db.flush()

    order = Order(
        code="TEMP",
        type=odata.get("type","OUTRIGHT"),
        status="ACTIVE" if odata.get("type") in ("RENTAL","INSTALLMENT") else "NEW",
        customer_id=customer.id,
        notes=odata.get("notes")
    )

    # Charges
    charges = odata.get("charges") or {}
    delivery_fee = _d(charges.get("delivery_fee"))
    return_fee  = _d(charges.get("return_delivery_fee"))
    penalty_fee = _d(charges.get("penalty_fee"))
    discount    = _d(charges.get("discount"))

    subtotal = Decimal("0.00")
    db.add(order); db.flush()

    for it in (odata.get("items") or []):
        qty = Decimal(str(it.get("qty",1)))
        unit = _d(it.get("unit_price"))
        line = _d(it.get("line_total")) if it.get("line_total") else (qty*unit)
        oi = OrderItem(order_id=order.id, name=it.get("name") or "Item", sku=it.get("sku"), category=it.get("category"),
                       item_type=it.get("item_type") or order.type, qty=qty, unit_price=unit, line_total=line)
        db.add(oi); subtotal += line

    total = subtotal - discount + delivery_fee + return_fee + penalty_fee
    paid = _d( (odata.get("totals") or {}).get("paid") )
    balance = total - paid

    order.subtotal = subtotal; order.discount = discount
    order.delivery_fee = delivery_fee; order.return_delivery_fee = return_fee; order.penalty_fee = penalty_fee
    order.total = total; order.paid_amount = paid; order.balance = balance

    # plan if any
    plan_data = odata.get("plan") or {}
    if plan_data.get("plan_type") in ("RENTAL","INSTALLMENT"):
        months = plan_data.get("months")
        start_s = plan_data.get("start_date")
        start_d = None
        try:
            if start_s: start_d = datetime.strptime(start_s, "%d/%m/%Y").date()
        except Exception:
            start_d = date.today()
        plan = Plan(order_id=order.id, plan_type=plan_data["plan_type"], months=months, monthly_amount=_d(plan_data.get("monthly_amount")), start_date=start_d)
        db.add(plan)

    # payment record if paid > 0 to respect cash basis now
    if paid > 0:
        p = Payment(order_id=order.id, date=date.today(), amount=paid, method="cash", reference="intake", category="ORDER")
        db.add(p)

    db.flush()
    order.code = generate_order_code(order.id)
    db.commit()
    db.refresh(order)
    return order
