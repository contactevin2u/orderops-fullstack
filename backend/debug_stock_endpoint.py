#!/usr/bin/env python3
"""
Quick debug endpoint to check what's actually in the database
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_session
from app.models.lorry_assignment import LorryAssignment
from app.models.lorry_stock_transaction import LorryStockTransaction
from datetime import date, datetime

debug_router = APIRouter(prefix="/debug-stock", tags=["debug"])

@debug_router.get("/check/{driver_id}")
async def debug_stock_check(driver_id: int, db: Session = Depends(get_session)):
    """Debug endpoint to check what's in the database"""
    
    today = date.today()
    result = {
        "driver_id": driver_id,
        "today": today.isoformat(),
        "assignments": [],
        "all_assignments": [],
        "stock_transactions": [],
        "lorry_stock": {}
    }
    
    # Get all assignments for this driver
    all_assignments = db.query(LorryAssignment).filter(
        LorryAssignment.driver_id == driver_id
    ).all()
    
    for a in all_assignments:
        result["all_assignments"].append({
            "id": a.id,
            "lorry_id": a.lorry_id,
            "assignment_date": a.assignment_date.isoformat(),
            "status": a.status,
            "stock_verified": a.stock_verified
        })
    
    # Get today's assignments
    today_assignments = db.query(LorryAssignment).filter(
        LorryAssignment.driver_id == driver_id,
        LorryAssignment.assignment_date == today
    ).all()
    
    for a in today_assignments:
        result["assignments"].append({
            "id": a.id,
            "lorry_id": a.lorry_id,
            "status": a.status,
            "stock_verified": a.stock_verified
        })
    
    # Get all stock transactions
    transactions = db.query(LorryStockTransaction).order_by(
        LorryStockTransaction.created_at.desc()
    ).limit(20).all()
    
    for t in transactions:
        result["stock_transactions"].append({
            "id": t.id,
            "lorry_id": t.lorry_id,
            "action": t.action,
            "uid": t.uid,
            "transaction_date": t.transaction_date.isoformat(),
            "created_at": t.created_at.isoformat()
        })
    
    # Get stock by lorry
    from collections import defaultdict
    stock_by_lorry = defaultdict(list)
    
    for t in transactions:
        if t.action == "LOAD":
            stock_by_lorry[t.lorry_id].append(t.uid)
        elif t.action == "UNLOAD":
            try:
                stock_by_lorry[t.lorry_id].remove(t.uid)
            except ValueError:
                pass  # UID not in list
    
    result["lorry_stock"] = dict(stock_by_lorry)
    
    return result

print("Add this debug endpoint to your main.py:")
print("from debug_stock_endpoint import debug_router")
print("app.include_router(debug_router)")
print()
print("Then call: GET /debug-stock/check/17")