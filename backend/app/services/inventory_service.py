from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import rapidfuzz.fuzz as fuzz

from ..models import SKU, Item, OrderItemUID, LorryStock, SKUAlias, Driver, Order
from ..models.item import ItemType, ItemStatus
from ..models.order_item_uid import UIDAction


class InventoryService:
    def __init__(self, session: Session):
        self.session = session

    def generate_uid(self, sku_id: int, driver_id: int, scan_date: date, item_type: ItemType = ItemType.RENTAL) -> str:
        """Generate UID in format: SKU001-DRV123-20240306-001"""
        sku = self.session.query(SKU).filter(SKU.id == sku_id).first()
        driver = self.session.query(Driver).filter(Driver.id == driver_id).first()
        
        if not sku or not driver:
            raise ValueError("Invalid SKU or Driver ID")
        
        # Create short codes
        sku_code = f"SKU{sku.id:03d}"
        driver_code = f"DRV{driver.id:03d}"
        date_str = scan_date.strftime("%Y%m%d")
        
        # Find next sequence number for this date
        existing_count = self.session.query(Item).filter(
            Item.uid.like(f"{sku_code}-{driver_code}-{date_str}-%")
        ).count()
        
        sequence = f"{existing_count + 1:03d}"
        
        # For NEW items, we need to generate 2 UIDs (copy 1 and copy 2)
        if item_type == ItemType.NEW:
            return f"{sku_code}-{driver_code}-{date_str}-{sequence}"
        else:
            return f"{sku_code}-{driver_code}-{date_str}-{sequence}"

    def generate_item_copies(self, sku_id: int, driver_id: int, scan_date: date, item_type: ItemType, serial_number: Optional[str] = None) -> List[Item]:
        """Generate item copies based on type (NEW=2 copies, RENTAL=1 copy)"""
        items = []
        
        if item_type == ItemType.NEW:
            # Generate 2 copies for new items
            base_uid = self.generate_uid(sku_id, driver_id, scan_date, item_type)
            for copy_num in [1, 2]:
                uid = f"{base_uid}-C{copy_num}"
                item = Item(
                    uid=uid,
                    sku_id=sku_id,
                    item_type=item_type,
                    copy_number=copy_num,
                    oem_serial=serial_number,
                    status=ItemStatus.WAREHOUSE,
                    current_driver_id=None
                )
                items.append(item)
        else:
            # Generate 1 copy for rental items
            uid = self.generate_uid(sku_id, driver_id, scan_date, item_type)
            item = Item(
                uid=uid,
                sku_id=sku_id,
                item_type=item_type,
                copy_number=None,
                oem_serial=serial_number,
                status=ItemStatus.WAREHOUSE,
                current_driver_id=None
            )
            items.append(item)
        
        return items

    def scan_uid_action(self, order_id: int, uid: str, action: UIDAction, scanned_by: int, sku_id: Optional[int] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        """Process UID scanning action and update item status"""
        # Find or create item
        item = self.session.query(Item).filter(Item.uid == uid).first()
        
        # If item doesn't exist and we have sku_id, this might be manual entry
        if not item and sku_id:
            # For manual entry, create a temporary item record
            sku = self.session.query(SKU).filter(SKU.id == sku_id).first()
            if not sku:
                raise ValueError("Invalid SKU ID")
            
            item = Item(
                uid=uid,
                sku_id=sku_id,
                item_type=ItemType.RENTAL,  # Default for manual entry
                status=ItemStatus.WAREHOUSE
            )
            self.session.add(item)
            self.session.flush()

        if not item:
            raise ValueError("UID not found in system")

        # Update item status based on action
        if action == UIDAction.LOAD_OUT:
            item.status = ItemStatus.WITH_DRIVER
            item.current_driver_id = scanned_by
        elif action == UIDAction.DELIVER:
            item.status = ItemStatus.DELIVERED
        elif action in [UIDAction.RETURN, UIDAction.LOAD_IN]:
            item.status = ItemStatus.RETURNED
            if action == UIDAction.LOAD_IN:
                item.current_driver_id = None
        elif action == UIDAction.REPAIR:
            item.status = ItemStatus.IN_REPAIR
        elif action == UIDAction.SWAP:
            # For swaps, mark as returned but keep notes about swap
            item.status = ItemStatus.RETURNED

        # Create UID scan record
        uid_record = OrderItemUID(
            order_id=order_id,
            uid=uid,
            scanned_by=scanned_by,
            action=action,
            sku_id=item.sku_id,
            sku_name=item.sku.name if item.sku else None,
            notes=notes
        )
        
        self.session.add(uid_record)
        self.session.commit()

        # UNIFIED: Also sync with lorry inventory system
        try:
            self._sync_to_lorry_system(order_id, uid, action, scanned_by, item.sku_id, notes)
        except Exception as e:
            # Don't fail the main operation if sync fails
            import logging
            logging.warning(f"Lorry system sync failed for UID {uid}: {e}")

        return {
            "success": True,
            "uid": uid,
            "action": action.value,
            "sku_name": item.sku.name if item.sku else None,
            "message": f"UID {uid} {action.value.lower()} processed successfully"
        }
    
    def _sync_to_lorry_system(self, order_id: int, uid: str, action: UIDAction, scanned_by: int, sku_id: int, notes: str = None):
        """Sync legacy inventory actions to the lorry transaction system"""
        try:
            from ..models import LorryAssignment, LorryStockTransaction, Driver
            from datetime import date, datetime
            
            # Get driver's current lorry assignment
            driver = self.session.get(Driver, scanned_by)
            if not driver:
                return
                
            today = date.today()
            assignment = self.session.execute(
                select(LorryAssignment).where(
                    and_(
                        LorryAssignment.driver_id == scanned_by,
                        LorryAssignment.assignment_date <= today
                    )
                ).order_by(LorryAssignment.assignment_date.desc()).limit(1)
            ).scalar_one_or_none()
            
            if not assignment:
                # Create virtual lorry for this driver if no assignment
                lorry_id = f"DRIVER_{scanned_by}"
            else:
                lorry_id = assignment.lorry_id
            
            # Map legacy actions to lorry actions
            lorry_action_map = {
                UIDAction.DELIVER: "DELIVERY",
                UIDAction.RETURN: "COLLECTION", 
                UIDAction.REPAIR: "REPAIR",
                UIDAction.SWAP: "DELIVERY",  # Swap is treated as delivery + collection
                UIDAction.LOAD_OUT: "LOAD",
                UIDAction.LOAD_IN: "UNLOAD"
            }
            
            if action not in lorry_action_map:
                return
                
            lorry_action = lorry_action_map[action]
            
            # Check if transaction already exists (avoid duplicates)
            existing = self.session.execute(
                select(LorryStockTransaction).where(
                    and_(
                        LorryStockTransaction.uid == uid,
                        LorryStockTransaction.action == lorry_action,
                        LorryStockTransaction.order_id == order_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                return  # Already synced
            
            # Create lorry transaction(s)
            now = datetime.now()
            transactions_to_add = []
            
            if action == UIDAction.SWAP:
                # SWAP requires two transactions: delivery of old item + collection of returned item
                # For simplicity, we'll create a single DELIVERY transaction with SWAP notes
                swap_transaction = LorryStockTransaction(
                    lorry_id=lorry_id,
                    action="DELIVERY",
                    uid=uid,
                    sku_id=sku_id,
                    order_id=order_id,
                    driver_id=scanned_by,
                    admin_user_id=scanned_by,
                    notes=f"SWAP transaction - Auto-sync from legacy: {notes or 'Item swapped'}",
                    transaction_date=now
                )
                transactions_to_add.append(swap_transaction)
            else:
                # Regular single transaction
                transaction = LorryStockTransaction(
                    lorry_id=lorry_id,
                    action=lorry_action,
                    uid=uid,
                    sku_id=sku_id,
                    order_id=order_id,
                    driver_id=scanned_by,
                    admin_user_id=scanned_by,
                    notes=f"Auto-sync from legacy system: {notes or action.value}",
                    transaction_date=now
                )
                transactions_to_add.append(transaction)
            
            # Add all transactions
            for transaction in transactions_to_add:
                self.session.add(transaction)
            
            self.session.commit()
            
            import logging
            logging.info(f"Synced legacy action {action.value} to lorry system: {uid} -> {lorry_id}")
            
        except Exception as e:
            import logging
            logging.error(f"Lorry system sync error: {e}")
            self.session.rollback()
            raise

    def get_order_uids(self, order_id: int) -> Dict[str, Any]:
        """Get all UID scans for an order"""
        uids = self.session.query(OrderItemUID).filter(
            OrderItemUID.order_id == order_id
        ).order_by(OrderItemUID.scanned_at.desc()).all()

        # Calculate totals by action
        totals = {}
        for action in UIDAction:
            totals[action.value.lower()] = len([u for u in uids if u.action == action])

        return {
            "order_id": order_id,
            "uids": [{
                "id": uid.id,
                "uid": uid.uid,
                "action": uid.action.value,
                "sku_id": uid.sku_id,
                "sku_name": uid.sku_name,
                "scanned_at": uid.scanned_at.isoformat(),
                "driver_name": uid.driver.name if uid.driver else None,
                "notes": uid.notes
            } for uid in uids],
            **totals
        }

    def get_driver_stock_status(self, driver_id: int) -> Dict[str, Any]:
        """Get current items with driver"""
        items = self.session.query(Item).filter(
            Item.current_driver_id == driver_id,
            Item.status == ItemStatus.WITH_DRIVER
        ).all()

        stock_by_sku = {}
        for item in items:
            sku_id = item.sku_id
            if sku_id not in stock_by_sku:
                stock_by_sku[sku_id] = {
                    "sku_name": item.sku.name,
                    "count": 0,
                    "items": []
                }
            stock_by_sku[sku_id]["count"] += 1
            stock_by_sku[sku_id]["items"].append({
                "uid": item.uid,
                "serial": item.oem_serial,
                "type": item.item_type.value,
                "copy_number": item.copy_number
            })

        return {
            "driver_id": driver_id,
            "stock_items": list(stock_by_sku.values()),
            "total_items": len(items)
        }

    def resolve_sku_name(self, query: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Resolve SKU name with exact, alias, and fuzzy matching"""
        if not query or not query.strip():
            return []

        query = query.strip().lower()
        matches = []

        # 1. Exact name match (case insensitive)
        exact_match = self.session.query(SKU).filter(
            func.lower(SKU.name) == query
        ).first()
        
        if exact_match:
            matches.append({
                "sku_id": exact_match.id,
                "sku_name": exact_match.name,
                "match_type": "exact",
                "confidence": 1.0
            })

        # 2. Alias match (case insensitive)
        alias_matches = self.session.query(SKUAlias).filter(
            func.lower(SKUAlias.alias) == query
        ).all()
        
        for alias in alias_matches:
            matches.append({
                "sku_id": alias.sku_id,
                "sku_name": alias.sku.name,
                "match_type": "alias",
                "confidence": 1.0
            })

        # 3. Fuzzy matching
        all_skus = self.session.query(SKU).all()
        fuzzy_matches = []
        
        for sku in all_skus:
            # Skip if already matched exactly
            if any(m["sku_id"] == sku.id and m["confidence"] == 1.0 for m in matches):
                continue
                
            # Calculate similarity
            similarity = fuzz.ratio(query, sku.name.lower()) / 100.0
            
            if similarity >= threshold:
                fuzzy_matches.append({
                    "sku_id": sku.id,
                    "sku_name": sku.name,
                    "match_type": "fuzzy",
                    "confidence": similarity
                })

        # Sort fuzzy matches by confidence
        fuzzy_matches.sort(key=lambda x: x["confidence"], reverse=True)
        matches.extend(fuzzy_matches)

        # Sort all matches by confidence (exact and alias first, then fuzzy)
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        return matches

    def get_sku_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get SKU name suggestions for partial matches"""
        if not query or not query.strip():
            return []

        query = query.strip().lower()
        
        # Get SKUs that contain the query string
        skus = self.session.query(SKU).filter(
            func.lower(SKU.name).contains(query)
        ).limit(limit * 2).all()  # Get more to filter better matches
        
        suggestions = []
        for sku in skus:
            suggestions.append(sku.name)
        
        return suggestions[:limit]

    def add_sku_alias(self, sku_id: int, alias: str) -> Dict[str, Any]:
        """Add alias for SKU"""
        # Check if alias already exists
        existing = self.session.query(SKUAlias).filter(
            func.lower(SKUAlias.alias) == alias.lower()
        ).first()
        
        if existing:
            raise ValueError("Alias already exists")

        sku_alias = SKUAlias(sku_id=sku_id, alias=alias)
        self.session.add(sku_alias)
        self.session.commit()

        return {
            "success": True,
            "alias_id": sku_alias.id,
            "message": "Alias added successfully"
        }