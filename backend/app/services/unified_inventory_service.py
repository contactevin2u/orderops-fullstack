"""
Unified Inventory Service - Single Source of Truth
Consolidates all inventory operations into lorry-based transaction system
World-class architecture with performance, reliability, and scalability
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func, or_
from sqlalchemy.exc import IntegrityError
import logging
import json
from enum import Enum

from ..models import (
    LorryStockTransaction, 
    LorryAssignment, 
    Lorry,
    Item,
    OrderItemUID,
    SKU,
    User,
    Driver,
    Order
)
from ..models.item import ItemStatus, ItemType
from ..models.order_item_uid import UIDAction


logger = logging.getLogger(__name__)


class InventoryAction(Enum):
    """Unified inventory actions"""
    # Admin stock management
    LOAD = "LOAD"                    # Admin loads stock into lorry
    UNLOAD = "UNLOAD"                # Admin unloads stock from lorry
    TRANSFER = "TRANSFER"            # Move between lorries
    ADJUSTMENT = "ADJUSTMENT"        # Stock correction
    
    # Driver operations  
    DELIVER = "DELIVER"              # Driver delivers to customer
    COLLECT = "COLLECT"              # Driver collects from customer
    REPAIR = "REPAIR"                # Send item for repair
    SWAP = "SWAP"                    # Swap item with customer
    
    # System operations
    RECEIVE = "RECEIVE"              # Receive new inventory
    DISPOSE = "DISPOSE"              # Dispose/write-off item


class LocationType(Enum):
    """Inventory location types"""
    WAREHOUSE = "WAREHOUSE"
    LORRY = "LORRY" 
    CUSTOMER = "CUSTOMER"
    REPAIR = "REPAIR"
    DISPOSED = "DISPOSED"


class UnifiedInventoryService:
    """
    World-class unified inventory service
    Single source of truth for all inventory operations
    High-performance, transaction-safe, audit-compliant
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    # ====================================================================
    # CORE INVENTORY OPERATIONS
    # ====================================================================
    
    def get_item_current_location(self, uid: str) -> Dict[str, Any]:
        """
        Get current location and status of any item
        High-performance single-query approach
        """
        # Get latest transaction for this UID
        latest_transaction = self.db.execute(
            select(LorryStockTransaction, User, Lorry)
            .join(User, LorryStockTransaction.admin_user_id == User.id, isouter=True)
            .join(Lorry, LorryStockTransaction.lorry_id == Lorry.lorry_id, isouter=True)
            .where(LorryStockTransaction.uid == uid)
            .order_by(LorryStockTransaction.transaction_date.desc())
            .limit(1)
        ).first()
        
        if not latest_transaction:
            return {
                "uid": uid,
                "location_type": LocationType.WAREHOUSE.value,
                "location_id": None,
                "location_name": "Warehouse",
                "status": "UNKNOWN",
                "last_updated": None,
                "last_action": None
            }
        
        transaction, user, lorry = latest_transaction
        
        # Determine current location based on last action
        location_type = LocationType.WAREHOUSE
        location_id = None
        location_name = "Warehouse"
        
        if transaction.action in ["LOAD", "COLLECT", "TRANSFER"]:
            location_type = LocationType.LORRY
            location_id = transaction.lorry_id
            location_name = f"Lorry {transaction.lorry_id}"
            if lorry:
                location_name += f" ({lorry.plate_number or 'No Plate'})"
                
        elif transaction.action == "DELIVER":
            location_type = LocationType.CUSTOMER
            location_id = transaction.order_id
            location_name = f"Customer (Order #{transaction.order_id})"
            
        elif transaction.action == "REPAIR":
            location_type = LocationType.REPAIR
            location_name = "Repair Facility"
            
        elif transaction.action in ["DISPOSE", "WRITE_OFF"]:
            location_type = LocationType.DISPOSED
            location_name = "Disposed"
        
        return {
            "uid": uid,
            "location_type": location_type.value,
            "location_id": location_id,
            "location_name": location_name,
            "status": transaction.action,
            "last_updated": transaction.transaction_date.isoformat(),
            "last_action": transaction.action,
            "last_action_by": user.username if user else "System",
            "notes": transaction.notes
        }
    
    def get_lorry_inventory(self, lorry_id: str, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get complete lorry inventory with performance optimization
        Returns current stock with SKU grouping and metadata
        """
        target_date = as_of_date or date.today()
        
        # High-performance query: get all transactions up to date
        transactions = self.db.execute(
            select(LorryStockTransaction, SKU)
            .join(SKU, LorryStockTransaction.sku_id == SKU.id, isouter=True)
            .where(
                and_(
                    LorryStockTransaction.lorry_id == lorry_id,
                    func.date(LorryStockTransaction.transaction_date) <= target_date
                )
            )
            .order_by(LorryStockTransaction.transaction_date.asc())
        ).all()
        
        # Calculate current stock with SKU metadata
        current_stock = {}  # uid -> transaction info
        sku_summary = {}   # sku_id -> count and metadata
        
        for transaction, sku in transactions:
            uid = transaction.uid
            
            # Apply stock addition/removal logic
            if transaction.action in ["LOAD", "COLLECT", "TRANSFER", "RECEIVE", "ADJUSTMENT"]:
                current_stock[uid] = {
                    "uid": uid,
                    "sku_id": transaction.sku_id,
                    "sku_code": sku.code if sku else f"SKU_{transaction.sku_id}",
                    "sku_name": sku.name if sku else "Unknown SKU",
                    "loaded_date": transaction.transaction_date.isoformat(),
                    "loaded_by": transaction.admin_user_id,
                    "notes": transaction.notes
                }
                
                # Update SKU summary
                sku_id = transaction.sku_id
                if sku_id not in sku_summary:
                    sku_summary[sku_id] = {
                        "sku_id": sku_id,
                        "sku_code": sku.code if sku else f"SKU_{sku_id}",
                        "sku_name": sku.name if sku else "Unknown SKU",
                        "count": 0,
                        "uids": []
                    }
                sku_summary[sku_id]["count"] += 1
                sku_summary[sku_id]["uids"].append(uid)
                
            elif transaction.action in ["UNLOAD", "DELIVER", "REPAIR", "DISPOSE", "ADJUSTMENT"]:
                if uid in current_stock:
                    # Remove from current stock
                    removed_item = current_stock.pop(uid)
                    
                    # Update SKU summary
                    sku_id = removed_item["sku_id"]
                    if sku_id in sku_summary:
                        sku_summary[sku_id]["count"] = max(0, sku_summary[sku_id]["count"] - 1)
                        if uid in sku_summary[sku_id]["uids"]:
                            sku_summary[sku_id]["uids"].remove(uid)
                        
                        # Remove empty SKU entries
                        if sku_summary[sku_id]["count"] == 0:
                            del sku_summary[sku_id]
        
        # Get lorry metadata
        lorry = self.db.execute(
            select(Lorry).where(Lorry.lorry_id == lorry_id)
        ).scalar_one_or_none()
        
        return {
            "lorry_id": lorry_id,
            "lorry_info": {
                "plate_number": lorry.plate_number if lorry else None,
                "model": lorry.model if lorry else None,
                "base_warehouse": lorry.base_warehouse if lorry else None
            },
            "as_of_date": target_date.isoformat(),
            "total_items": len(current_stock),
            "total_skus": len(sku_summary),
            "current_stock": list(current_stock.values()),
            "sku_summary": list(sku_summary.values())
        }
    
    def process_stock_transaction(
        self,
        lorry_id: str,
        action: InventoryAction,
        uids: List[str],
        user_id: int,
        order_id: Optional[int] = None,
        driver_id: Optional[int] = None,
        notes: Optional[str] = None,
        target_lorry_id: Optional[str] = None  # For transfers
    ) -> Dict[str, Any]:
        """
        Process stock transactions with full validation and atomic operations
        World-class transaction safety with comprehensive error handling
        """
        logger.info(f"Processing {action.value} for {len(uids)} UIDs in lorry {lorry_id}")
        
        now = datetime.now()
        successful_transactions = []
        errors = []
        
        # Pre-validation: Check current stock state
        current_stock = set()
        if action in [InventoryAction.UNLOAD, InventoryAction.DELIVER, InventoryAction.TRANSFER]:
            current_inventory = self.get_lorry_inventory(lorry_id)
            current_stock = {item["uid"] for item in current_inventory["current_stock"]}
        
        # Process each UID with validation
        for uid in uids:
            try:
                # Validate UID exists if required
                if action in [InventoryAction.UNLOAD, InventoryAction.DELIVER, InventoryAction.TRANSFER]:
                    if uid not in current_stock:
                        errors.append(f"UID {uid} not found in lorry {lorry_id}")
                        continue
                
                # Validate against duplicates for additions
                if action in [InventoryAction.LOAD, InventoryAction.COLLECT, InventoryAction.RECEIVE]:
                    if uid in current_stock:
                        errors.append(f"UID {uid} already exists in lorry {lorry_id}")
                        continue
                
                # Get SKU ID for this UID (try multiple sources)
                sku_id = self._get_sku_id_for_uid(uid)
                
                # Create transaction record
                transaction = LorryStockTransaction(
                    lorry_id=lorry_id,
                    action=action.value,
                    uid=uid,
                    sku_id=sku_id,
                    order_id=order_id,
                    driver_id=driver_id,
                    admin_user_id=user_id,
                    notes=notes,
                    transaction_date=now
                )
                
                self.db.add(transaction)
                successful_transactions.append(transaction)
                
                # For transfers, create corresponding LOAD transaction in target lorry
                if action == InventoryAction.TRANSFER and target_lorry_id:
                    transfer_transaction = LorryStockTransaction(
                        lorry_id=target_lorry_id,
                        action=InventoryAction.LOAD.value,
                        uid=uid,
                        sku_id=sku_id,
                        order_id=order_id,
                        driver_id=driver_id,
                        admin_user_id=user_id,
                        notes=f"Transfer from {lorry_id}: {notes or ''}",
                        transaction_date=now
                    )
                    self.db.add(transfer_transaction)
                    successful_transactions.append(transfer_transaction)
                
            except Exception as e:
                logger.error(f"Error processing UID {uid}: {e}")
                errors.append(f"Failed to process UID {uid}: {str(e)}")
        
        # Atomic commit
        try:
            self.db.commit()
            
            # Refresh all transactions
            for transaction in successful_transactions:
                self.db.refresh(transaction)
                
            logger.info(f"Successfully processed {len(successful_transactions)} transactions")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Transaction commit failed: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "processed_count": 0,
                "errors": errors + [str(e)]
            }
        
        return {
            "success": len(errors) == 0,
            "message": f"Successfully processed {len(successful_transactions)} {action.value} transactions",
            "processed_count": len(successful_transactions),
            "errors": errors,
            "transaction_ids": [t.id for t in successful_transactions]
        }
    
    def _get_sku_id_for_uid(self, uid: str) -> Optional[int]:
        """
        Intelligent SKU ID resolution from multiple sources
        Handles both legacy and new UID formats
        """
        # Try to get from existing Item record first
        item = self.db.execute(
            select(Item).where(Item.uid == uid)
        ).scalar_one_or_none()
        
        if item:
            return item.sku_id
        
        # Try to extract from UID format: SKU004-ADMIN-20250910-001
        try:
            if uid.startswith("SKU") and "|SKU:" in uid:
                # New format: UID:SKU004-ADMIN-20250910-001|SKU:4|TYPE:RENTAL
                sku_part = uid.split("|SKU:")[1].split("|")[0]
                return int(sku_part)
            elif uid.startswith("SKU"):
                # Legacy format: SKU004-ADMIN-20250910-001
                sku_code = uid.split("-")[0]
                sku_id = int(sku_code.replace("SKU", ""))
                return sku_id
        except (ValueError, IndexError):
            pass
        
        # Try to find by exact UID in transactions
        existing_transaction = self.db.execute(
            select(LorryStockTransaction).where(
                LorryStockTransaction.uid == uid
            ).limit(1)
        ).scalar_one_or_none()
        
        if existing_transaction:
            return existing_transaction.sku_id
        
        # Last resort: return None and let caller handle
        logger.warning(f"Could not determine SKU ID for UID: {uid}")
        return None
    
    # ====================================================================
    # MIGRATION & DATA CONSOLIDATION
    # ====================================================================
    
    def migrate_legacy_data(self) -> Dict[str, Any]:
        """
        Migrate all legacy Item and OrderItemUID data to unified system
        One-time migration with comprehensive validation
        """
        logger.info("Starting legacy data migration to unified inventory system")
        
        migration_stats = {
            "items_migrated": 0,
            "order_actions_migrated": 0,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Step 1: Migrate Item records to initial LOAD transactions
            items = self.db.execute(
                select(Item).where(Item.status != ItemStatus.DISCONTINUED)
            ).scalars().all()
            
            for item in items:
                try:
                    # Determine appropriate initial action based on status
                    if item.status == ItemStatus.WAREHOUSE:
                        # Create initial LOAD transaction for warehouse items
                        initial_transaction = LorryStockTransaction(
                            lorry_id="WAREHOUSE",  # Virtual warehouse lorry
                            action="RECEIVE",
                            uid=item.uid,
                            sku_id=item.sku_id,
                            admin_user_id=1,  # System user
                            notes=f"Migrated from legacy Item table - Status: {item.status.value}",
                            transaction_date=item.created_at or datetime.now()
                        )
                        self.db.add(initial_transaction)
                        migration_stats["items_migrated"] += 1
                        
                    elif item.status == ItemStatus.WITH_DRIVER and item.current_driver_id:
                        # Find driver's current lorry assignment
                        assignment = self.db.execute(
                            select(LorryAssignment).where(
                                and_(
                                    LorryAssignment.driver_id == item.current_driver_id,
                                    LorryAssignment.assignment_date <= date.today()
                                )
                            ).order_by(LorryAssignment.assignment_date.desc()).limit(1)
                        ).scalar_one_or_none()
                        
                        lorry_id = assignment.lorry_id if assignment else f"DRIVER_{item.current_driver_id}"
                        
                        # Create LOAD transaction for driver items
                        driver_transaction = LorryStockTransaction(
                            lorry_id=lorry_id,
                            action="LOAD",
                            uid=item.uid,
                            sku_id=item.sku_id,
                            driver_id=item.current_driver_id,
                            admin_user_id=1,
                            notes=f"Migrated from legacy Item table - With driver",
                            transaction_date=item.created_at or datetime.now()
                        )
                        self.db.add(driver_transaction)
                        migration_stats["items_migrated"] += 1
                        
                except Exception as e:
                    error_msg = f"Failed to migrate item {item.uid}: {str(e)}"
                    logger.error(error_msg)
                    migration_stats["errors"].append(error_msg)
            
            # Step 2: Migrate OrderItemUID records to transactions
            uid_actions = self.db.execute(
                select(OrderItemUID, Item).join(Item, OrderItemUID.uid == Item.uid)
                .order_by(OrderItemUID.scanned_at.asc())
            ).all()
            
            for uid_action, item in uid_actions:
                try:
                    # Map legacy actions to new inventory actions
                    action_mapping = {
                        UIDAction.DELIVER: InventoryAction.DELIVER,
                        UIDAction.RETURN: InventoryAction.COLLECT,
                        UIDAction.REPAIR: InventoryAction.REPAIR,
                        UIDAction.LOAD_OUT: InventoryAction.LOAD,
                        UIDAction.LOAD_IN: InventoryAction.UNLOAD
                    }
                    
                    if uid_action.action not in action_mapping:
                        continue
                    
                    new_action = action_mapping[uid_action.action]
                    
                    # Determine lorry ID
                    driver_assignment = self.db.execute(
                        select(LorryAssignment).where(
                            and_(
                                LorryAssignment.driver_id == uid_action.scanned_by,
                                LorryAssignment.assignment_date <= uid_action.scanned_at.date()
                            )
                        ).order_by(LorryAssignment.assignment_date.desc()).limit(1)
                    ).scalar_one_or_none()
                    
                    lorry_id = driver_assignment.lorry_id if driver_assignment else f"DRIVER_{uid_action.scanned_by}"
                    
                    # Create corresponding transaction
                    migrated_transaction = LorryStockTransaction(
                        lorry_id=lorry_id,
                        action=new_action.value,
                        uid=uid_action.uid,
                        sku_id=item.sku_id,
                        order_id=uid_action.order_id,
                        driver_id=uid_action.scanned_by,
                        admin_user_id=1,  # System migration user
                        notes=f"Migrated from OrderItemUID - Original: {uid_action.action.value}",
                        transaction_date=uid_action.scanned_at
                    )
                    self.db.add(migrated_transaction)
                    migration_stats["order_actions_migrated"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to migrate UID action {uid_action.id}: {str(e)}"
                    logger.error(error_msg)
                    migration_stats["errors"].append(error_msg)
            
            # Commit migration
            self.db.commit()
            logger.info(f"Migration completed successfully: {migration_stats}")
            
        except Exception as e:
            self.db.rollback()
            error_msg = f"Migration failed: {str(e)}"
            logger.error(error_msg)
            migration_stats["errors"].append(error_msg)
        
        return migration_stats
    
    # ====================================================================
    # REPORTING & ANALYTICS
    # ====================================================================
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive inventory summary across all locations
        High-performance dashboard data
        """
        # Get all active lorries
        lorries = self.db.execute(
            select(Lorry).where(Lorry.is_active == True)
        ).scalars().all()
        
        summary = {
            "total_lorries": len(lorries),
            "total_items": 0,
            "lorry_inventories": [],
            "warehouse_items": 0,
            "customer_items": 0,
            "repair_items": 0,
            "top_skus": []
        }
        
        # Collect inventory for each lorry
        for lorry in lorries:
            inventory = self.get_lorry_inventory(lorry.lorry_id)
            summary["lorry_inventories"].append({
                "lorry_id": lorry.lorry_id,
                "plate_number": lorry.plate_number,
                "item_count": inventory["total_items"],
                "sku_count": inventory["total_skus"]
            })
            summary["total_items"] += inventory["total_items"]
        
        # Get location distribution
        location_stats = self.db.execute(
            select(
                LorryStockTransaction.action,
                func.count(LorryStockTransaction.uid).label("count")
            ).select_from(
                select(
                    LorryStockTransaction.uid,
                    LorryStockTransaction.action,
                    func.row_number().over(
                        partition_by=LorryStockTransaction.uid,
                        order_by=LorryStockTransaction.transaction_date.desc()
                    ).label("rn")
                ).subquery()
            ).where(
                select().column("rn") == 1
            ).group_by(LorryStockTransaction.action)
        ).all()
        
        for action, count in location_stats:
            if action in ["LOAD", "COLLECT", "RECEIVE"]:
                # Items in lorries (already counted above)
                pass
            elif action == "DELIVER":
                summary["customer_items"] += count
            elif action == "REPAIR":
                summary["repair_items"] += count
            elif action == "UNLOAD":
                summary["warehouse_items"] += count
        
        return summary
    
    def get_transaction_history(
        self,
        lorry_id: Optional[str] = None,
        uid: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get filtered transaction history with rich metadata
        Optimized for reporting and audit trails
        """
        query = select(
            LorryStockTransaction,
            User,
            Driver,
            SKU,
            Lorry
        ).join(
            User, LorryStockTransaction.admin_user_id == User.id, isouter=True
        ).join(
            Driver, LorryStockTransaction.driver_id == Driver.id, isouter=True
        ).join(
            SKU, LorryStockTransaction.sku_id == SKU.id, isouter=True
        ).join(
            Lorry, LorryStockTransaction.lorry_id == Lorry.lorry_id, isouter=True
        )
        
        # Apply filters
        filters = []
        if lorry_id:
            filters.append(LorryStockTransaction.lorry_id == lorry_id)
        if uid:
            filters.append(LorryStockTransaction.uid == uid)
        if start_date:
            filters.append(func.date(LorryStockTransaction.transaction_date) >= start_date)
        if end_date:
            filters.append(func.date(LorryStockTransaction.transaction_date) <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(LorryStockTransaction.transaction_date.desc()).limit(limit)
        
        results = self.db.execute(query).all()
        
        history = []
        for transaction, user, driver, sku, lorry in results:
            history.append({
                "id": transaction.id,
                "uid": transaction.uid,
                "action": transaction.action,
                "lorry_id": transaction.lorry_id,
                "lorry_info": {
                    "plate_number": lorry.plate_number if lorry else None,
                    "model": lorry.model if lorry else None
                },
                "sku_info": {
                    "id": sku.id if sku else None,
                    "code": sku.code if sku else None,
                    "name": sku.name if sku else None
                },
                "order_id": transaction.order_id,
                "driver_info": {
                    "id": driver.id if driver else None,
                    "name": driver.name if driver else None
                },
                "admin_user": user.username if user else "System",
                "notes": transaction.notes,
                "transaction_date": transaction.transaction_date.isoformat(),
                "created_at": transaction.created_at.isoformat()
            })
        
        return history