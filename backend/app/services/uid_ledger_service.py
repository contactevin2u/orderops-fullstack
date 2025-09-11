from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import logging

from ..models import UIDLedgerEntry, LedgerEntrySource, UIDAction, Item, SKU, Driver, User, Order
from ..models.uid_ledger import UIDLedgerEntry


logger = logging.getLogger(__name__)


class UIDLedgerService:
    """
    Service for managing the comprehensive UID scan ledger for medical device traceability.
    Every scan across the system should be recorded here for audit purposes.
    """
    
    def __init__(self, session: Session):
        self.session = session

    def record_scan(
        self,
        uid: str,
        action: UIDAction,
        recorded_by: int,  # Admin user ID who is recording this
        scanned_by_admin: Optional[int] = None,
        scanned_by_driver: Optional[int] = None,
        scanner_name: Optional[str] = None,
        order_id: Optional[int] = None,
        sku_id: Optional[int] = None,
        source: LedgerEntrySource = LedgerEntrySource.ADMIN_MANUAL,
        lorry_id: Optional[str] = None,
        location_notes: Optional[str] = None,
        notes: Optional[str] = None,
        customer_name: Optional[str] = None,
        order_reference: Optional[str] = None,
        driver_scan_id: Optional[str] = None,
        scanned_at: Optional[datetime] = None
    ) -> UIDLedgerEntry:
        """
        Record a UID scan in the comprehensive ledger.
        
        Args:
            uid: The UID that was scanned
            action: What action was performed (LOAD_OUT, DELIVER, etc.)
            recorded_by: Admin user ID who is recording this entry
            scanned_by_admin: Admin user ID who physically scanned (if different from recorded_by)
            scanned_by_driver: Driver ID who physically scanned
            scanner_name: Name of scanner if no user/driver FK available
            order_id: Associated order (if any)
            sku_id: SKU ID for manual entry cases
            source: Where this scan originated from
            lorry_id: Which lorry/truck
            location_notes: Free-form location description
            notes: Additional notes
            customer_name: Customer context for deliveries
            order_reference: Order code/reference
            driver_scan_id: Reference to driver app scan record
            scanned_at: When scan occurred (defaults to now)
        """
        
        # Input validation
        if not uid or not uid.strip():
            raise ValueError("UID cannot be empty")
        
        if len(uid) > 255:  # Reasonable UID length limit
            raise ValueError("UID too long (max 255 characters)")
            
        if not isinstance(action, UIDAction):
            raise ValueError("action must be a UIDAction enum")
            
        if not recorded_by or recorded_by <= 0:
            raise ValueError("recorded_by must be a valid user ID")
            
        # Validate that at least one scanner is identified
        if not scanned_by_admin and not scanned_by_driver and not scanner_name:
            raise ValueError("At least one scanner identification required (admin, driver, or name)")
            
        # Validate mutually exclusive scanner types
        if scanned_by_admin and scanned_by_driver:
            raise ValueError("Scanner cannot be both admin and driver simultaneously")
            
        # String length validations
        if notes and len(notes) > 2000:
            raise ValueError("Notes too long (max 2000 characters)")
            
        if customer_name and len(customer_name) > 255:
            raise ValueError("Customer name too long (max 255 characters)")
            
        if order_reference and len(order_reference) > 255:
            raise ValueError("Order reference too long (max 255 characters)")
            
        if lorry_id and len(lorry_id) > 50:
            raise ValueError("Lorry ID too long (max 50 characters)")
        
        # Validate UID exists (but allow manual entries)
        item = self.session.query(Item).filter(Item.uid == uid).first()
        if not item and not sku_id:
            logger.warning(f"UID {uid} not found in system and no SKU provided")
        
        # Auto-populate order reference if order_id provided
        if order_id and not order_reference:
            order = self.session.query(Order).filter(Order.id == order_id).first()
            if order:
                order_reference = order.code
                if not customer_name and hasattr(order, 'customer_name'):
                    customer_name = order.customer_name

        # Create ledger entry
        entry = UIDLedgerEntry(
            uid=uid,
            action=action,
            scanned_at=scanned_at or datetime.now(),
            scanned_by_admin=scanned_by_admin,
            scanned_by_driver=scanned_by_driver,
            scanner_name=scanner_name,
            order_id=order_id,
            sku_id=sku_id or (item.sku_id if item else None),
            source=source,
            lorry_id=lorry_id,
            location_notes=location_notes,
            notes=notes,
            customer_name=customer_name,
            order_reference=order_reference,
            driver_scan_id=driver_scan_id,
            recorded_by=recorded_by
        )
        
        self.session.add(entry)
        
        try:
            self.session.commit()
            logger.info(f"Recorded UID scan: {uid} {action.value} by {scanner_name or scanned_by_admin or scanned_by_driver}")
            return entry
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to record UID scan: {uid} {action.value} - {e}")
            raise

    def record_from_driver_sync(
        self,
        uid: str,
        action: UIDAction,
        driver_id: int,
        recorded_by: int,
        order_id: Optional[int] = None,
        notes: Optional[str] = None,
        driver_scan_id: Optional[str] = None,
        scanned_at: Optional[datetime] = None
    ) -> UIDLedgerEntry:
        """
        Record a scan that came from driver app sync.
        """
        
        # Get driver info for context
        driver = self.session.query(Driver).filter(Driver.id == driver_id).first()
        scanner_name = driver.name if driver else f"Driver {driver_id}"
        
        return self.record_scan(
            uid=uid,
            action=action,
            recorded_by=recorded_by,
            scanned_by_driver=driver_id,
            scanner_name=scanner_name,
            order_id=order_id,
            source=LedgerEntrySource.DRIVER_SYNC,
            notes=notes,
            driver_scan_id=driver_scan_id,
            scanned_at=scanned_at
        )

    def record_from_order_operation(
        self,
        uid: str,
        action: UIDAction,
        order_id: int,
        scanned_by: int,
        recorded_by: int,
        notes: Optional[str] = None,
        is_driver: bool = False
    ) -> UIDLedgerEntry:
        """
        Record a scan from order fulfillment operations.
        """
        
        return self.record_scan(
            uid=uid,
            action=action,
            recorded_by=recorded_by,
            scanned_by_admin=scanned_by if not is_driver else None,
            scanned_by_driver=scanned_by if is_driver else None,
            order_id=order_id,
            source=LedgerEntrySource.ORDER_OPERATION,
            notes=notes
        )

    def get_uid_history(self, uid: str) -> List[Dict[str, Any]]:
        """
        Get complete scan history for a specific UID for traceability.
        """
        
        entries = self.session.query(UIDLedgerEntry).filter(
            UIDLedgerEntry.uid == uid,
            UIDLedgerEntry.is_deleted == False
        ).order_by(desc(UIDLedgerEntry.scanned_at)).all()
        
        history = []
        for entry in entries:
            scanner_info = self._get_scanner_info(entry)
            
            history.append({
                "id": entry.id,
                "uid": entry.uid,
                "action": entry.action.value,
                "scanned_at": entry.scanned_at.isoformat(),
                "scanner": scanner_info,
                "source": entry.source.value,
                "order_id": entry.order_id,
                "order_reference": entry.order_reference,
                "customer_name": entry.customer_name,
                "lorry_id": entry.lorry_id,
                "location_notes": entry.location_notes,
                "notes": entry.notes,
                "recorded_at": entry.recorded_at.isoformat()
            })
        
        return history

    def get_audit_trail(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        uid: Optional[str] = None,
        action: Optional[UIDAction] = None,
        scanner_id: Optional[int] = None,
        order_id: Optional[int] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Get audit trail for medical device traceability reporting.
        """
        
        query = self.session.query(UIDLedgerEntry).filter(
            UIDLedgerEntry.is_deleted == False
        )
        
        # Apply filters
        if start_date:
            query = query.filter(UIDLedgerEntry.scanned_at >= start_date)
        if end_date:
            query = query.filter(UIDLedgerEntry.scanned_at <= end_date)
        if uid:
            query = query.filter(UIDLedgerEntry.uid == uid)
        if action:
            query = query.filter(UIDLedgerEntry.action == action)
        if scanner_id:
            query = query.filter(
                or_(
                    UIDLedgerEntry.scanned_by_admin == scanner_id,
                    UIDLedgerEntry.scanned_by_driver == scanner_id
                )
            )
        if order_id:
            query = query.filter(UIDLedgerEntry.order_id == order_id)
        
        # Get results
        total_count = query.count()
        entries = query.order_by(desc(UIDLedgerEntry.scanned_at)).limit(limit).all()
        
        # Format results
        audit_entries = []
        for entry in entries:
            scanner_info = self._get_scanner_info(entry)
            
            audit_entries.append({
                "id": entry.id,
                "uid": entry.uid,
                "action": entry.action.value,
                "scanned_at": entry.scanned_at.isoformat(),
                "scanner": scanner_info,
                "source": entry.source.value,
                "order_id": entry.order_id,
                "order_reference": entry.order_reference,
                "customer_name": entry.customer_name,
                "location": {
                    "lorry_id": entry.lorry_id,
                    "notes": entry.location_notes
                },
                "notes": entry.notes,
                "item_info": self._get_item_info(entry.uid),
                "recorded_at": entry.recorded_at.isoformat()
            })
        
        # Calculate summary stats
        action_counts = {}
        for action_enum in UIDAction:
            count = query.filter(UIDLedgerEntry.action == action_enum).count()
            if count > 0:
                action_counts[action_enum.value] = count
        
        return {
            "total_entries": total_count,
            "entries": audit_entries,
            "summary": {
                "actions": action_counts,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
        }

    def _get_scanner_info(self, entry: UIDLedgerEntry) -> Dict[str, Any]:
        """Get formatted scanner information."""
        
        if entry.scanned_by_admin:
            admin = self.session.query(User).filter(User.id == entry.scanned_by_admin).first()
            return {
                "type": "admin",
                "id": entry.scanned_by_admin,
                "name": admin.name if admin else f"Admin {entry.scanned_by_admin}"
            }
        elif entry.scanned_by_driver:
            driver = self.session.query(Driver).filter(Driver.id == entry.scanned_by_driver).first()
            return {
                "type": "driver", 
                "id": entry.scanned_by_driver,
                "name": driver.name if driver else f"Driver {entry.scanned_by_driver}"
            }
        else:
            return {
                "type": "manual",
                "name": entry.scanner_name or "Unknown"
            }

    def _get_item_info(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get item information for the UID."""
        
        item = self.session.query(Item).filter(Item.uid == uid).first()
        if not item:
            return None
            
        return {
            "uid": item.uid,
            "sku_id": item.sku_id,
            "sku_name": item.sku.name if item.sku else None,
            "item_type": item.item_type.value,
            "status": item.status.value,
            "oem_serial": item.oem_serial
        }

    def soft_delete_entry(self, entry_id: int, deleted_by: int, reason: str) -> bool:
        """
        Soft delete a ledger entry (for corrections, not true deletion).
        Medical device traceability requires maintaining audit trail.
        """
        
        entry = self.session.query(UIDLedgerEntry).filter(UIDLedgerEntry.id == entry_id).first()
        if not entry:
            return False
            
        entry.is_deleted = True
        entry.deleted_at = datetime.now()
        entry.deleted_by = deleted_by
        entry.deletion_reason = reason
        
        self.session.commit()
        
        logger.info(f"Soft deleted ledger entry {entry_id}: {reason}")
        return True
    
    def record_bulk_scans(self, scan_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Record multiple UID scans in a single transaction for better performance.
        
        Args:
            scan_entries: List of dictionaries containing scan data
        
        Returns:
            Dictionary with success count and any errors
        """
        success_count = 0
        errors = []
        
        try:
            # Use bulk insert for better performance
            ledger_entries = []
            
            for entry_data in scan_entries:
                try:
                    # Validate each entry
                    if not entry_data.get('uid') or not entry_data.get('action'):
                        errors.append(f"Missing required fields in entry: {entry_data}")
                        continue
                        
                    # Create ledger entry object
                    entry = UIDLedgerEntry(
                        uid=entry_data['uid'],
                        action=entry_data['action'],
                        scanned_at=entry_data.get('scanned_at', datetime.now()),
                        scanned_by_admin=entry_data.get('scanned_by_admin'),
                        scanned_by_driver=entry_data.get('scanned_by_driver'),
                        scanner_name=entry_data.get('scanner_name'),
                        order_id=entry_data.get('order_id'),
                        sku_id=entry_data.get('sku_id'),
                        source=entry_data.get('source', LedgerEntrySource.ADMIN_MANUAL),
                        lorry_id=entry_data.get('lorry_id'),
                        location_notes=entry_data.get('location_notes'),
                        notes=entry_data.get('notes'),
                        customer_name=entry_data.get('customer_name'),
                        order_reference=entry_data.get('order_reference'),
                        driver_scan_id=entry_data.get('driver_scan_id'),
                        recorded_by=entry_data['recorded_by']
                    )
                    
                    ledger_entries.append(entry)
                    
                except Exception as e:
                    errors.append(f"Failed to prepare entry for UID {entry_data.get('uid', 'unknown')}: {e}")
            
            # Bulk insert all valid entries
            if ledger_entries:
                self.session.add_all(ledger_entries)
                self.session.commit()
                success_count = len(ledger_entries)
                
                logger.info(f"Bulk recorded {success_count} UID scans in ledger")
            
            return {
                "success": True,
                "success_count": success_count,
                "total_requested": len(scan_entries),
                "errors": errors
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Bulk UID scan recording failed: {e}")
            return {
                "success": False,
                "success_count": 0,
                "total_requested": len(scan_entries),
                "errors": [f"Bulk operation failed: {e}"] + errors
            }

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get ledger statistics for dashboard."""
        
        start_date = datetime.now().date() - date.timedelta(days=days)
        
        total_scans = self.session.query(UIDLedgerEntry).filter(
            UIDLedgerEntry.scanned_at >= start_date,
            UIDLedgerEntry.is_deleted == False
        ).count()
        
        # Scans by action
        action_stats = {}
        for action in UIDAction:
            count = self.session.query(UIDLedgerEntry).filter(
                UIDLedgerEntry.action == action,
                UIDLedgerEntry.scanned_at >= start_date,
                UIDLedgerEntry.is_deleted == False
            ).count()
            action_stats[action.value] = count
        
        # Scans by source
        source_stats = {}
        for source in LedgerEntrySource:
            count = self.session.query(UIDLedgerEntry).filter(
                UIDLedgerEntry.source == source,
                UIDLedgerEntry.scanned_at >= start_date,
                UIDLedgerEntry.is_deleted == False
            ).count()
            source_stats[source.value] = count
        
        return {
            "period_days": days,
            "total_scans": total_scans,
            "scans_by_action": action_stats,
            "scans_by_source": source_stats
        }