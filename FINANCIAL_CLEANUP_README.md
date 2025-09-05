# Financial Calculation Cleanup Documentation

## Overview
This commit represents an aggressive cleanup of complex financial calculation logic that was causing bugs and maintenance issues. The approach was to **break things temporarily** and **keep core flows intact** for a future clean rewrite.

## What Was Deleted

### 1. Complex Outstanding Calculations (`backend/app/reports/outstanding.py`)

**REMOVED**: 120+ lines of complex calculation logic
- `months_elapsed()` - Complex month calculation with cutoff handling  
- `calculate_plan_due()` - Multi-priority start date logic, accrual cutoffs
- `compute_expected_for_order()` - 60+ line function with delivery validation, plan accrual logic
- **REPLACED WITH**: Simple field access (`order.total`, `order.balance`)

**Key Deleted Logic**:
```python
# DELETED: Complex month-based accrual
months = min(
    months_elapsed(start, as_of, cutoff=cutoff),
    getattr(plan, "months", None) or 10 ** 6,
)
additional_months = max(months - 1, 0)  # Exclude first month
plan_accrual = monthly_amount * additional_months

# DELETED: Delivery status validation  
trip_status = getattr(trip, "status", None) if trip else None
is_delivered = trip_status in {"DELIVERED", "SUCCESS", "COMPLETED"}
```

### 2. First Month Fee Generation (`backend/app/services/ordersvc.py`)

**REMOVED**: Auto-generation of "First Month Rental/Instalment" fee lines
- `ensure_first_month_fee_line()` - 50+ line function detecting and creating fee lines
- `ensure_plan_first_month_fee()` - Order-level fee injection with recomputation
- **REPLACED WITH**: No-op function

**Key Deleted Logic**:
```python
# DELETED: Auto-generate first month fees
fee_line = {
    "name": f"First Month {'Rental' if plan_type == 'RENTAL' else 'Instalment'}",
    "item_type": "FEE",
    "sku": "FIRST_MONTH", 
    "qty": 1,
    "unit_price": monthly_amount,
    "line_total": monthly_amount,
}
plan.upfront_billed_amount = monthly_amount
```

### 3. Return/Cancel Validation (`backend/app/services/status_updates.py`)

**REMOVED**: Business rule validation before status changes
- Outstanding balance validation for rental returns
- Principal vs fee payment separation for installment cancellations  
- Complex accrual cutoff logic with `returned_at` timestamps
- **REPLACED WITH**: Simple status updates only

**Key Deleted Logic**:
```python
# DELETED: Rental return validation
if order.type == "RENTAL" and not collect:
    outstanding_balance = compute_balance(order, as_of_date, trip)
    if outstanding_balance > DEC0:
        raise ValueError("Outstanding must be cleared before return")

# DELETED: Payment categorization
fee_categories = {"DELIVERY", "PENALTY", "FEE"}
for payment in all_payments:
    if payment.category in fee_categories:
        fee_paid += payment_amount
    else:
        principal_paid += payment_amount
```

### 4. Plan Creation Inference (`backend/app/services/ordersvc.py`)

**REMOVED**: Complex plan type and monthly amount detection
- Auto-detection of plan type from item types
- Monthly amount aggregation from multiple items
- Special handling for rental/installment item pricing
- **REPLACED WITH**: Simple direct assignment

**Key Deleted Logic**:
```python
# DELETED: Plan type inference
if plan_type not in ("INSTALLMENT", "RENTAL"):
    for it in items:
        if it["item_type"] in {"RENTAL", "INSTALLMENT"}:
            plan_type = it["item_type"]
            break

# DELETED: Monthly amount aggregation
if monthly_amount <= 0:
    monthly_candidates = []
    for it in items:
        if it.get("monthly_amount") > 0:
            monthly_candidates.append(it["monthly_amount"])
    monthly_amount = sum(monthly_candidates)
```

### 5. Financial Test Files

**REMOVED**: Complex test scenarios
- `test_plan_math.py` - Month calculation tests
- `test_due_cancel_no_double_count.py` - Outstanding validation tests  
- `test_patch_plan_item_zero_pricing.py` - Plan pricing tests
- `test_order_plan_update.py` - Plan update tests

### 6. Duplicate Frontend Calculations

**REMOVED**: Fallback calculation displays
- Static balance fallback in order details page
- Multiple duplicate `normalizeParsedForOrder` functions (consolidated to api.ts)
- Old parsing endpoint with complex normalization logic

### 7. Supporting Modules

**REMOVED**: Utility modules
- `backend/app/services/plan_math.py` - Complete file deleted
- Complex import chains and unused calculation utilities

## Current State (What Still Works)

### ✅ Core Flows Intact:
- Order creation with items and plans
- Payment recording and status updates
- Return/cancellation status changes  
- Plan data storage (plan_type, monthly_amount, months)
- Frontend displays and forms

### ❌ What's Broken (Temporarily):
- No monthly accrual calculations
- No first month fee auto-generation
- No outstanding validation on returns
- No delivery-based calculation triggers
- Static totals only (no dynamic outstanding)

## Key Business Rules to Restore (Clean Rewrite)

### RENTAL Orders:
1. **Item Creation**: `line_total = 0` (plan carries pricing)
2. **First Month Fee**: Auto-generate "First Month Rental" FEE line = `monthly_amount`
3. **Accrual**: After delivery, accrue `monthly_amount` per month (unlimited)
4. **Return**: Validate outstanding cleared unless `collect=true`

### INSTALLMENT Orders:
1. **Item Creation**: `line_total = 0` (plan carries pricing)  
2. **First Month Fee**: Auto-generate "First Month Instalment" FEE line = `monthly_amount`
3. **Accrual**: After delivery, accrue monthly (capped at total `plan.months`)
4. **Cancel**: Allow outstanding, separate principal from fee payments

### Simple Outstanding Formula (Target):
```python
def compute_expected_for_order(order, as_of_date):
    base = order.subtotal - order.discount + fees
    
    if not delivered or order_type == "OUTRIGHT":
        return base
        
    months_since_delivery = months_between(delivery_date, as_of_date, returned_at)
    
    if order_type in ["RENTAL", "INSTALLMENT"]:
        additional_months = max(months_since_delivery - 1, 0)  # First month in subtotal
        if order_type == "INSTALLMENT":
            additional_months = min(additional_months, plan.months - 1)  # Cap installment
        accrual = plan.monthly_amount * additional_months
    else:
        accrual = 0
        
    return base + accrual
```

## Rewrite Strategy (Future)

1. **Phase 1**: Simple month calculation utility
2. **Phase 2**: Rebuild first month fee injection  
3. **Phase 3**: Add delivery-based accrual trigger
4. **Phase 4**: Restore return/cancel validation
5. **Phase 5**: Integration testing

## Philosophy
- **Break complex, fix simple**: Delete 500+ lines of buggy complexity, rebuild 50 lines cleanly
- **Keep data intact**: All order/plan/payment data preserved  
- **Fail fast**: Better to break temporarily than maintain buggy calculations
- **Single responsibility**: Each function does one thing well

---
*This cleanup prioritizes maintainability over feature completeness. The system can process orders and payments but outstanding calculations are temporarily simplified until clean rewrite.*