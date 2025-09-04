#!/usr/bin/env python3

import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Add the app directory to Python path
sys.path.insert(0, '.')

from app.db import SessionLocal, get_session
from app.models.order import Order
from app.models.plan import Plan
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.trip import Trip
from app.reports.outstanding import compute_expected_for_order, compute_balance, months_elapsed
from app.services.ordersvc import _sum_posted_payments

def debug_order_111():
    """Debug order 111 outstanding calculation"""
    if SessionLocal:
        db = SessionLocal()
    else:
        # Use get_session if SessionLocal is not available
        db = next(get_session())
    
    try:
        # Get order 111
        order = db.query(Order).filter(Order.id == 111).first()
        if not order:
            print(f"❌ Order 111 not found")
            return
            
        print(f"🔍 DEBUG ORDER 111 ({order.code})")
        print("=" * 60)
        
        # Basic order info
        print(f"📋 ORDER DETAILS:")
        print(f"   ID: {order.id}")
        print(f"   Code: {order.code}")
        print(f"   Type: {order.type}")
        print(f"   Status: {order.status}")
        print(f"   Delivery Date: {order.delivery_date}")
        print(f"   Returned At: {order.returned_at}")
        print(f"   Created: {order.created_at}")
        print()
        
        # Financial details
        print(f"💰 FINANCIAL DETAILS:")
        print(f"   Subtotal: RM {order.subtotal}")
        print(f"   Discount: RM {order.discount}")
        print(f"   Delivery Fee: RM {order.delivery_fee}")
        print(f"   Return Delivery Fee: RM {order.return_delivery_fee}")
        print(f"   Penalty Fee: RM {order.penalty_fee}")
        print(f"   Total: RM {order.total}")
        print(f"   Paid Amount: RM {order.paid_amount}")
        print(f"   Balance: RM {order.balance}")
        print()
        
        # Items
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        print(f"📦 ORDER ITEMS ({len(items)}):")
        for item in items:
            print(f"   - {item.name} ({item.item_type})")
            print(f"     SKU: {item.sku}, Category: {item.category}")
            print(f"     Qty: {item.qty}, Unit Price: RM {item.unit_price}")
            print(f"     Line Total: RM {item.line_total}")
        print()
        
        # Plan details
        plan = order.plan
        if plan:
            print(f"📅 PLAN DETAILS:")
            print(f"   Plan Type: {plan.plan_type}")
            print(f"   Start Date: {plan.start_date}")
            print(f"   Months: {plan.months}")
            print(f"   Monthly Amount: RM {plan.monthly_amount}")
            print(f"   Upfront Billed: RM {plan.upfront_billed_amount}")
            print(f"   Status: {plan.status}")
            print()
        else:
            print(f"📅 No plan attached to order")
            print()
            
        # Trip details
        trip = order.trip
        if trip:
            print(f"🚛 TRIP DETAILS:")
            print(f"   Status: {trip.status}")
            print(f"   Delivered At: {trip.delivered_at}")
            print(f"   Route ID: {trip.route_id}")
            print()
        else:
            print(f"🚛 No trip attached to order")
            print()
            
        # Payments
        payments = db.query(Payment).filter(Payment.order_id == order.id, Payment.status == 'POSTED').all()
        total_payments = sum(p.amount for p in payments)
        print(f"💳 PAYMENTS ({len(payments)}):")
        for payment in payments:
            print(f"   - RM {payment.amount} ({payment.method}) - {payment.created_at}")
        print(f"   Total Payments: RM {total_payments}")
        print()
        
        # Outstanding calculation
        as_of = date.today()
        print(f"🧮 OUTSTANDING CALCULATION (as of {as_of}):")
        
        try:
            expected = compute_expected_for_order(order, as_of, trip)
            balance = compute_balance(order, as_of, trip)
            paid = _sum_posted_payments(order)
            
            print(f"   Expected Amount: RM {expected}")
            print(f"   Paid Amount: RM {paid}")
            print(f"   Outstanding Balance: RM {balance}")
            print()
            
            # Detailed calculation breakdown
            if plan and plan.monthly_amount and trip and trip.status in {"DELIVERED", "SUCCESS", "COMPLETED"}:
                print(f"🔢 ACCRUAL BREAKDOWN:")
                
                start = plan.start_date
                if not start and trip.delivered_at:
                    start = trip.delivered_at.date() if hasattr(trip.delivered_at, 'date') else trip.delivered_at
                if not start and order.delivery_date:
                    start = order.delivery_date.date() if hasattr(order.delivery_date, 'date') else order.delivery_date
                    
                cutoff = order.returned_at
                if cutoff and hasattr(cutoff, 'date'):
                    cutoff = cutoff.date()
                    
                print(f"   Start Date: {start}")
                print(f"   Cutoff Date: {cutoff}")
                print(f"   As Of Date: {as_of}")
                
                if start:
                    months = months_elapsed(start, as_of, cutoff=cutoff)
                    if plan.months:
                        months = min(months, plan.months)
                    additional_months = max(months - 1, 0)
                    plan_accrual = Decimal(str(plan.monthly_amount or 0)) * additional_months
                    
                    print(f"   Total Months Elapsed: {months}")
                    print(f"   Additional Months (excl. first): {additional_months}")
                    print(f"   Monthly Amount: RM {plan.monthly_amount}")
                    print(f"   Plan Accrual: RM {plan_accrual}")
            
        except Exception as e:
            print(f"❌ Error calculating outstanding: {e}")
            import traceback
            traceback.print_exc()
            
        # Child orders (adjustments)
        adjustments = db.query(Order).filter(Order.parent_id == order.id).all()
        if adjustments:
            print(f"🔗 ADJUSTMENT ORDERS ({len(adjustments)}):")
            for adj in adjustments:
                print(f"   - {adj.code} ({adj.type}) - Status: {adj.status}")
                print(f"     Total: RM {adj.total}, Balance: RM {adj.balance}")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_order_111()