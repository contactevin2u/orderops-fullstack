"""Lorry Inventory Service for real-time stock tracking"""

from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func
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


class LorryInventoryService:
    """Service for managing lorry stock in real-time"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_current_stock(self, lorry_id: str, as_of_date: Optional[date] = None) -> List[str]:
        """Get current UIDs in the specified lorry"""
        target_date = as_of_date or date.today()
        
        # Get all transactions for this lorry up to the target date
        transactions = self.db.execute(
            select(LorryStockTransaction)
            .where(
                and_(
                    LorryStockTransaction.lorry_id == lorry_id,
                    func.date(LorryStockTransaction.transaction_date) <= target_date
                )
            )
            .order_by(LorryStockTransaction.transaction_date.asc())
        ).scalars().all()
        
        # Process transactions to determine current stock
        current_stock = set()
        
        for transaction in transactions:
            if transaction.is_stock_addition:
                current_stock.add(transaction.uid)
            elif transaction.is_stock_removal:
                current_stock.discard(transaction.uid)
        
        logger.info(f"Current stock for lorry {lorry_id}: {len(current_stock)} items")
        return list(current_stock)
    
    def load_uids(
        self, 
        lorry_id: str, 
        uids: List[str], 
        admin_user_id: int, 
        notes: Optional[str] = None
    ) -> Dict[str, any]:
        """Admin loads UIDs into a lorry"""
        now = datetime.now()
        transactions_added = []
        errors = []
        
        for uid in uids:
            try:
                # Check if UID already exists in lorry
                existing_stock = self.get_current_stock(lorry_id)
                if uid in existing_stock:
                    errors.append(f"UID {uid} already exists in lorry {lorry_id}")
                    continue
                
                # Create load transaction
                transaction = LorryStockTransaction(
                    lorry_id=lorry_id,
                    action="LOAD",
                    uid=uid,
                    admin_user_id=admin_user_id,
                    notes=notes,
                    transaction_date=now
                )
                
                self.db.add(transaction)
                transactions_added.append(transaction)
                
            except Exception as e:
                errors.append(f"Failed to load UID {uid}: {str(e)}")
                logger.error(f"Error loading UID {uid}: {e}")
        
        # Commit all successful transactions
        try:
            self.db.commit()
            for transaction in transactions_added:
                self.db.refresh(transaction)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit load transactions: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "loaded_count": 0,
                "errors": errors + [str(e)]
            }
        
        logger.info(f"Loaded {len(transactions_added)} UIDs into lorry {lorry_id}")
        
        return {
            "success": True,
            "message": f"Successfully loaded {len(transactions_added)} UIDs into lorry {lorry_id}",
            "loaded_count": len(transactions_added),
            "errors": errors
        }
    
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
        uid_actions: List[Dict[str, any]],
        admin_user_id: int = 1  # System user for automatic actions
    ) -> Dict[str, any]:
        """Process UID actions from delivery and update lorry inventory"""
        now = datetime.now()
        transactions_added = []
        errors = []
        
        for action_data in uid_actions:
            try:
                action = action_data.get("action")
                uid = action_data.get("uid")
                notes = action_data.get("notes", f"Order {order_id} - {action}")
                
                if action == "DELIVER":
                    # Remove from lorry (delivered to customer)
                    transaction = LorryStockTransaction(
                        lorry_id=lorry_id,
                        action="DELIVERY",
                        uid=uid,
                        order_id=order_id,
                        driver_id=driver_id,
                        admin_user_id=admin_user_id,
                        notes=notes,
                        transaction_date=now
                    )
                elif action in ["COLLECT", "REPAIR"]:
                    # Add to lorry (collected from customer)
                    transaction = LorryStockTransaction(
                        lorry_id=lorry_id,
                        action="COLLECTION",
                        uid=uid,
                        order_id=order_id,
                        driver_id=driver_id,
                        admin_user_id=admin_user_id,
                        notes=notes,
                        transaction_date=now
                    )
                elif action == "SWAP":
                    # Handle swap as both delivery and collection
                    # This might need special handling for two UIDs
                    transaction = LorryStockTransaction(
                        lorry_id=lorry_id,
                        action="DELIVERY",  # First UID delivered
                        uid=uid,
                        order_id=order_id,
                        driver_id=driver_id,
                        admin_user_id=admin_user_id,
                        notes=f"SWAP - {notes}",
                        transaction_date=now
                    )
                else:
                    errors.append(f"Unknown action: {action}")
                    continue
                
                self.db.add(transaction)
                transactions_added.append(transaction)
                
            except Exception as e:
                errors.append(f"Failed to process action {action_data}: {str(e)}")
                logger.error(f"Error processing delivery action: {e}")
        
        # Commit all successful transactions
        try:
            self.db.commit()
            for transaction in transactions_added:
                self.db.refresh(transaction)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit delivery transactions: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "processed_count": 0,
                "errors": errors + [str(e)]
            }
        
        logger.info(f"Processed {len(transactions_added)} delivery actions for lorry {lorry_id}")
        
        return {
            "success": True,
            "message": f"Successfully processed {len(transactions_added)} delivery actions",
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
        query = select(LorryStockTransaction, User).join(
            User, LorryStockTransaction.admin_user_id == User.id
        ).order_by(LorryStockTransaction.transaction_date.desc())
        
        if lorry_id:
            query = query.where(LorryStockTransaction.lorry_id == lorry_id)
        
        if start_date:
            query = query.where(func.date(LorryStockTransaction.transaction_date) >= start_date)
        
        if end_date:
            query = query.where(func.date(LorryStockTransaction.transaction_date) <= end_date)
        
        query = query.limit(limit)
        
        results = self.db.execute(query).all()
        
        transactions = []
        for transaction, user in results:
            transactions.append({
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
            })
        
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