from pydantic import BaseModel, Field
from typing import Optional, List

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
    type: str  # OUTRIGHT|INSTALLMENT|RENTAL
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

class OrderOut(BaseModel):
    id: int
    code: str
    type: str
    status: str
    subtotal: float
    total: float
    paid_amount: float
    balance: float

    class Config:
        from_attributes = True
