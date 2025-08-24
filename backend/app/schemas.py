from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field
import datetime as dt

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
    qty: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    line_total: Decimal = Decimal("0")

class PlanIn(BaseModel):
    plan_type: str  # RENTAL|INSTALLMENT
    months: Optional[int] = None
    monthly_amount: Decimal = Decimal("0")
    start_date: Optional[str] = None

class ChargesIn(BaseModel):
    delivery_fee: Decimal = Decimal("0")
    return_delivery_fee: Decimal = Decimal("0")
    penalty_fee: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")

class TotalsIn(BaseModel):
    subtotal: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    paid: Decimal = Decimal("0")
    to_collect: Decimal = Decimal("0")

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
    qty: Decimal
    unit_price: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True


class PaymentOut(BaseModel):
    id: int
    amount: Decimal
    date: Optional[dt.date] = None
    method: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: int
    plan_type: str
    start_date: Optional[dt.date] = None
    months: Optional[int] = None
    monthly_amount: Decimal = Decimal("0")
    status: str

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    code: str
    type: str
    status: str
    delivery_date: Optional[dt.date] = None
    notes: Optional[str] = None
    subtotal: Decimal
    discount: Decimal | None = Decimal("0")
    delivery_fee: Decimal | None = Decimal("0")
    return_delivery_fee: Decimal | None = Decimal("0")
    penalty_fee: Decimal | None = Decimal("0")
    total: Decimal
    paid_amount: Decimal
    balance: Decimal
    customer: Optional[CustomerOut] = None
    items: List[OrderItemOut] = Field(default_factory=list)
    payments: List[PaymentOut] = Field(default_factory=list)
    plan: Optional[PlanOut] = None

    class Config:
        from_attributes = True


class DeviceRegisterIn(BaseModel):
    fcm_token: str
    platform: str


class DriverOut(BaseModel):
    id: int
    name: str | None = None
    phone: str | None = None

    class Config:
        from_attributes = True


class AssignDriverIn(BaseModel):
    driver_id: int
