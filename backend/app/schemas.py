from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class CustomerIn(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    map_url: Optional[str] = None

class ItemIn(BaseModel):
    name: str
    sku: Optional[str] = None
    category: Optional[str] = None  # BED|WHEELCHAIR|OXYGEN|ACCESSORY
    item_type: str  # OUTRIGHT|INSTALLMENT|RENTAL|FEE
    qty: float = 1
    unit_price: float = 0
    line_total: float = 0

class PlanIn(BaseModel):
    plan_type: str  # RENTAL|INSTALLMENT
    months: Optional[int] = None
    monthly_amount: float = 0
    start_date: Optional[str] = None

class ChargesIn(BaseModel):
    delivery_fee: float = 0
    return_delivery_fee: float = 0
    penalty_fee: float = 0
    discount: float = 0

class TotalsIn(BaseModel):
    subtotal: float = 0
    total: float = 0
    paid: float = 0
    to_collect: float = 0

class OrderBlock(BaseModel):
    type: str  # OUTRIGHT|INSTALLMENT|RENTAL|MIXED
    delivery_date: Optional[str] = None
    notes: Optional[str] = None
    items: List[ItemIn] = Field(default_factory=list)
    charges: ChargesIn = ChargesIn()
    plan: Optional[PlanIn] = None
    totals: TotalsIn = TotalsIn()

class ParsedOrder(BaseModel):
    customer: CustomerIn
    order: OrderBlock

class OrderCreateIn(BaseModel):
    parsed: ParsedOrder

class CustomerOut(BaseModel):
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    map_url: Optional[str] = None

    class Config:
        from_attributes = True


class OrderItemOut(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    item_type: str
    qty: float
    unit_price: float
    line_total: float

    class Config:
        from_attributes = True


class PaymentOut(BaseModel):
    id: int
    amount: float
    # Use ``date`` so ORM values validate and FastAPI serializes to ISO strings.
    date: Optional[date] = None
    method: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: int
    plan_type: str
    start_date: Optional[date] = None
    months: Optional[int] = None
    monthly_amount: float = 0
    status: str

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    code: str
    type: str
    status: str
    delivery_date: Optional[date] = None
    notes: Optional[str] = None
    subtotal: float
    discount: float | None = 0
    delivery_fee: float | None = 0
    return_delivery_fee: float | None = 0
    penalty_fee: float | None = 0
    total: float
    paid_amount: float
    balance: float
    customer: Optional[CustomerOut] = None
    items: List[OrderItemOut] = Field(default_factory=list)
    payments: List[PaymentOut] = Field(default_factory=list)
    plan: Optional[PlanOut] = None

    class Config:
        from_attributes = True
