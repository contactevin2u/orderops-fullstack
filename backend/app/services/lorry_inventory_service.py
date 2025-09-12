"""Lorry Inventory Service for real-time stock tracking"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func, literal_column
import json
import logging

from ..models import (
    LorryStockTransaction, 
    LorryAssignment, 
    LorryStockVerification,
    SKU,
    User
)


logger = logging.getLogger(__name__)

IN_ACTIONS = ("LOAD", "COLLECTION")
OUT_ACTIONS = ("UNLOAD", "DELIVERY")

def _kl_day_bounds(d: date) -> Tuple[datetime, datetime]:
    # Asia/Kuala_Lumpur is UTC+8 with no DST; compute [start, end) and convert to UTC for DB timestamps
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    end_local = start_local + timedelta(days=1)
    return (start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc))

class LorryInventoryService:
    """Service for managing lorry stock in real-time"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_current_stock(self, lorry_id: str, as_of_date: Optional[date] = None) -> List[str]:
        """
        UID state as-of end of 'as_of_date' business day (KL). Uses latest action per (lorry, uid).
        """
        target_date = as_of_date or date.today()
        start_utc, end_utc = _kl_day_bounds(target_date)

        t = LorryStockTransaction

        # row_number() over (lorry_id, uid) by transaction_date desc, id desc
        rn = func.row_number().over(
            partition_by=(t.lorry_id, t.uid),
            order_by=(t.transaction_date.desc(), t.id.desc())
        ).label("rn")

        subq = (
            select(t.lorry_id, t.uid, t.action, rn)
            .where(
                and_(
                    t.lorry_id == lorry_id,
                    t.transaction_date < end_utc  # half-open: include all events strictly before next day 00:00 KL
                )
            )
        ).subquery()

        rows = self.db.execute(
            select(subq.c.uid, subq.c.action).where(subq.c.rn == 1)
        ).all()

        return [uid for (uid, action) in rows if action in IN_ACTIONS]
    
    def has_transaction_history(self, lorry_id: str) -> bool:
        """Check if a lorry has any transaction history"""
        transaction_count = self.db.execute(
            select(func.count(LorryStockTransaction.id))
            .where(LorryStockTransaction.lorry_id == lorry_id)
        ).scalar()
        
        return transaction_count > 0
    
    def load_uids(
        self, 
        lorry_id: str, 
        uids: List[str], 
        admin_user_id: int, 
        notes: Optional[str] = None
    ) -> Dict[str, any]:
        """Admin loads UIDs into a lorry"""
        logger.info(f"=== LORRY INVENTORY SERVICE load_uids DEBUG START ===")
        logger.info(f"DEBUG: lorry_id={lorry_id}, uids_count={len(uids)}, admin_user_id={admin_user_id}, notes={notes}")
        
        now = datetime.now()
        transactions_added = []
        errors = []
        
        # Get current stock ONCE at the beginning to avoid performance issues
        existing_stock = set(self.get_current_stock(lorry_id))
        logger.info(f"DEBUG: Current stock contains {len(existing_stock)} UIDs")
        
        # Keep track of UIDs being added in this batch to prevent duplicates within the batch
        uids_being_added = set()
        
        logger.info(f"DEBUG: Processing {len(uids)} UIDs: {uids[:5]}{'...' if len(uids) > 5 else ''}")
        
        for i, uid in enumerate(uids):
            logger.info(f"DEBUG: Processing UID {i+1}/{len(uids)}: {uid}")
            try:
                # Check if UID already exists in current stock
                if uid in existing_stock:
                    logger.warning(f"DEBUG: UID {uid} already exists in lorry {lorry_id}")
                    errors.append(f"UID {uid} already exists in lorry {lorry_id}")
                    continue
                
                # Check if UID is being added in this same batch
                if uid in uids_being_added:
                    logger.warning(f"DEBUG: UID {uid} is duplicate within this batch for lorry {lorry_id}")
                    errors.append(f"UID {uid} is duplicate within this batch")
                    continue
                
                # Create load transaction
                logger.info(f"DEBUG: Creating LorryStockTransaction for UID {uid}")
                transaction = LorryStockTransaction(
                    lorry_id=lorry_id,
                    action="LOAD",
                    uid=uid,
                    admin_user_id=admin_user_id,
                    notes=notes,
                    transaction_date=now
                )
                logger.info(f"DEBUG: LorryStockTransaction created - {transaction}")
                
                self.db.add(transaction)
                logger.info(f"DEBUG: Transaction added to session")
                transactions_added.append(transaction)
                uids_being_added.add(uid)  # Track this UID as being added
                logger.info(f"DEBUG: Transaction appended to list - total added: {len(transactions_added)}")
                
            except Exception as e:
                errors.append(f"Failed to load UID {uid}: {str(e)}")
                logger.error(f"Error loading UID {uid}: {e}")
        
        # Commit all successful transactions
        logger.info(f"DEBUG: About to commit {len(transactions_added)} transactions")
        try:
            self.db.commit()
            logger.info(f"DEBUG: Database commit successful")
            
            for i, transaction in enumerate(transactions_added):
                logger.info(f"DEBUG: Refreshing transaction {i+1}/{len(transactions_added)}")
                self.db.refresh(transaction)
                logger.info(f"DEBUG: Transaction {i+1} refreshed - ID: {transaction.id}")
                
        except Exception as e:
            logger.error(f"DEBUG: Database commit failed: {e}")
            logger.error(f"DEBUG: Exception type: {type(e)}")
            self.db.rollback()
            logger.error(f"Failed to commit load transactions: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "loaded_count": 0,
                "errors": errors + [str(e)]
            }
        
        # Legacy sync removed - using unified LorryStockTransaction system only
        logger.info("Using unified transaction system - legacy sync disabled")
        
        logger.info(f"Loaded {len(transactions_added)} UIDs into lorry {lorry_id}")
        
        result = {
            "success": True,
            "message": f"Successfully loaded {len(transactions_added)} UIDs into lorry {lorry_id}",
            "loaded_count": len(transactions_added),
            "errors": errors
        }
        
        logger.info(f"=== LORRY INVENTORY SERVICE load_uids DEBUG END === returning: {result}")
        return result
    
    def unload_uids(
        self, 
        lorry_id: str, 
        uids: List[str], 
        admin_user_id: int, 
        notes: Optional[str] = None
    ) -> Dict[str, any]:
        """Admin unloads UIDs from a lorry"""
        now = datetime.now()
        transactions_added = []
        errors = []
        
        # Get current stock to validate unload requests
        current_stock = set(self.get_current_stock(lorry_id))
        
        for uid in uids:
            try:
                # Check if UID exists in lorry
                if uid not in current_stock:
                    errors.append(f"UID {uid} not found in lorry {lorry_id}")
                    continue
                
                # Create unload transaction
                transaction = LorryStockTransaction(
                    lorry_id=lorry_id,
                    action="UNLOAD",
                    uid=uid,
                    admin_user_id=admin_user_id,
                    notes=notes,
                    transaction_date=now
                )
                
                self.db.add(transaction)
                transactions_added.append(transaction)
                
            except Exception as e:
                errors.append(f"Failed to unload UID {uid}: {str(e)}")
                logger.error(f"Error unloading UID {uid}: {e}")
        
        # Commit all successful transactions
        try:
            self.db.commit()
            for transaction in transactions_added:
                self.db.refresh(transaction)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit unload transactions: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "unloaded_count": 0,
                "errors": errors + [str(e)]
            }
        
        # Legacy sync removed - using unified LorryStockTransaction system only
        logger.info("Using unified transaction system - legacy sync disabled")
        
        logger.info(f"Unloaded {len(transactions_added)} UIDs from lorry {lorry_id}")
        
        return {
            "success": True,
            "message": f"Successfully unloaded {len(transactions_added)} UIDs from lorry {lorry_id}",
            "unloaded_count": len(transactions_added),
            "errors": errors
        }
    
    def process_delivery_actions(
        self,
        lorry_id: str,
        order_id: int,
        driver_id: int,
        uid_actions: List[Dict[str, Any]],
        admin_user_id: Optional[int] = None,
        ensure_in_lorry: bool = True
    ) -> Dict[str, Any]:
        """Process UID actions and update lorry inventory atomically"""
        now = datetime.now(timezone.utc)
        errors: List[str] = []
        transactions_added: List[LorryStockTransaction] = []

        # Preload current state once for quick membership checks
        current_stock: Set[str] = set(self.get_current_stock(lorry_id, now.date()))

        def _add_tx(action: str, uid: str, notes: str):
            tx = LorryStockTransaction(
                lorry_id=lorry_id,
                action=action,
                uid=uid,
                order_id=order_id,
                driver_id=driver_id,
                admin_user_id=admin_user_id,
                notes=notes,
                transaction_date=now
            )
            self.db.add(tx)
            transactions_added.append(tx)

        try:
            for action_data in uid_actions:
                action = action_data.get("action")
                uid = action_data.get("uid")
                notes = action_data.get("notes", f"Order {order_id} - {action}")

                if not uid or not action:
                    errors.append("Missing action or uid")
                    continue

                if action == "DELIVER":
                    if ensure_in_lorry and uid not in current_stock:
                        errors.append(f"UID not in lorry: {uid}")
                        continue
                    _add_tx("DELIVERY", uid, notes)
                    current_stock.discard(uid)

                elif action in ("COLLECT", "REPAIR"):
                    _add_tx("COLLECTION", uid, notes)
                    current_stock.add(uid)

                elif action == "SWAP":
                    deliver_uid = action_data.get("deliver_uid") or uid
                    collect_uid = action_data.get("collect_uid")
                    if not deliver_uid or not collect_uid:
                        errors.append("SWAP requires deliver_uid and collect_uid")
                        continue
                    if ensure_in_lorry and deliver_uid not in current_stock:
                        errors.append(f"SWAP deliver UID not in lorry: {deliver_uid}")
                        continue
                    _add_tx("DELIVERY", deliver_uid, f"SWAP OUT - {notes}")
                    current_stock.discard(deliver_uid)
                    _add_tx("COLLECTION", collect_uid, f"SWAP IN - {notes}")
                    current_stock.add(collect_uid)

                else:
                    errors.append(f"Unknown action: {action}")

            self.db.commit()
            for tx in transactions_added:
                self.db.refresh(tx)

        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "processed_count": 0,
                "errors": errors + [str(e)]
            }

        return {
            "success": len(errors) == 0,
            "message": f"Successfully processed {len(transactions_added)} action(s)",
            "processed_count": len(transactions_added),
            "errors": errors
        }
    
    def get_stock_transactions(
        self, 
        lorry_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, any]]:
        """Get stock transaction history"""
        logger.info(f"=== LORRY INVENTORY SERVICE get_stock_transactions DEBUG START ===")
        logger.info(f"DEBUG: lorry_id={lorry_id}, start_date={start_date}, end_date={end_date}, limit={limit}")
        
        try:
            query = select(LorryStockTransaction, User).join(
                User, LorryStockTransaction.admin_user_id == User.id, isouter=True  # LEFT JOIN since admin_user_id can be NULL
            ).order_by(LorryStockTransaction.transaction_date.desc())
            logger.info(f"DEBUG: Base query created")
        except Exception as e:
            logger.error(f"DEBUG: Error creating base query: {e}")
            raise
        
        try:
            if lorry_id:
                logger.info(f"DEBUG: Adding lorry_id filter: {lorry_id}")
                query = query.where(LorryStockTransaction.lorry_id == lorry_id)
            
            if start_date:
                logger.info(f"DEBUG: Adding start_date filter: {start_date}")
                query = query.where(func.date(LorryStockTransaction.transaction_date) >= start_date)
            
            if end_date:
                logger.info(f"DEBUG: Adding end_date filter: {end_date}")
                query = query.where(func.date(LorryStockTransaction.transaction_date) <= end_date)
            
            logger.info(f"DEBUG: Adding limit: {limit}")
            query = query.limit(limit)
            
            logger.info(f"DEBUG: About to execute query")
            results = self.db.execute(query).all()
            logger.info(f"DEBUG: Query executed - got {len(results)} results")
            
        except Exception as e:
            logger.error(f"DEBUG: Error executing query: {e}")
            logger.error(f"DEBUG: Exception type: {type(e)}")
            raise
        
        transactions = []
        logger.info(f"DEBUG: Processing {len(results)} results into transaction list")
        
        for i, (transaction, user) in enumerate(results):
            logger.info(f"DEBUG: Processing result {i+1}/{len(results)} - Transaction ID: {transaction.id}")
            try:
                tx_dict = {
                    "id": transaction.id,
                    "lorry_id": transaction.lorry_id,
                    "action": transaction.action,
                    "uid": transaction.uid,
                    "sku_id": transaction.sku_id,
                    "order_id": transaction.order_id,
                    "driver_id": transaction.driver_id,
                    "admin_user": user.username if user else "Unknown",
                    "notes": transaction.notes,
                    "transaction_date": transaction.transaction_date.isoformat(),
                    "created_at": transaction.created_at.isoformat()
                }
                transactions.append(tx_dict)
                logger.info(f"DEBUG: Transaction {i+1} processed: {tx_dict}")
            except Exception as e:
                logger.error(f"DEBUG: Error processing transaction {i+1}: {e}")
                continue
        
        logger.info(f"=== LORRY INVENTORY SERVICE get_stock_transactions DEBUG END === returning {len(transactions)} transactions")
        return transactions
    
    def get_lorry_inventory_summary(self) -> Dict[str, any]:
        """Get summary of all lorry inventories"""
        # Get all unique lorries that have transactions
        lorries = self.db.execute(
            select(LorryStockTransaction.lorry_id)
            .distinct()
            .order_by(LorryStockTransaction.lorry_id)
        ).scalars().all()
        
        summary = []
        for lorry_id in lorries:
            current_stock = self.get_current_stock(lorry_id)
            
            summary.append({
                "lorry_id": lorry_id,
                "current_stock_count": len(current_stock),
                "current_uids": current_stock[:10],  # First 10 for preview
                "has_more": len(current_stock) > 10
            })
        
        return {
            "total_lorries": len(summary),
            "lorries": summary
        }