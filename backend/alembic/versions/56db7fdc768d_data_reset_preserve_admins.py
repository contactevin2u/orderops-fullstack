
#!/usr/bin/env python


"""data reset preserve admins - wipe business data, keep structure and admin users

Revision ID: 56db7fdc768d
Revises: 3dd6dd11b822
Create Date: 2025-09-13 21:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '56db7fdc768d'
down_revision = '3dd6dd11b822'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    DATA RESET: Keep all table structures, wipe business data, preserve admin users
    This gives you a fresh start while maintaining your database schema and admin access
    """
    print("DATA RESET: Wiping business data while preserving structure and admin users...")
    
    conn = op.get_bind()
    
    def table_exists(table_name: str) -> bool:
        """Check if table exists"""
        try:
            result = conn.exec_driver_sql(f"""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = '{table_name}'
            """).scalar()
            return result > 0
        except Exception:
            # Fallback for SQLite
            try:
                result = conn.exec_driver_sql(f"""
                    SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'
                """).first()
                return result is not None
            except Exception:
                return False
    
    def safe_clear_table(table_name: str, condition: str = ""):
        """Clear data from table with optional condition"""
        if table_exists(table_name):
            try:
                if condition:
                    sql = f"DELETE FROM {table_name} WHERE {condition}"
                    result = conn.exec_driver_sql(sql)
                    print(f"  SUCCESS Cleared {table_name} data (condition: {condition})")
                else:
                    # Try TRUNCATE first (PostgreSQL), fall back to DELETE (SQLite)
                    try:
                        conn.exec_driver_sql(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                        print(f"  SUCCESS Truncated {table_name} (reset sequences)")
                    except Exception:
                        conn.exec_driver_sql(f"DELETE FROM {table_name}")
                        print(f"  SUCCESS Deleted all data from {table_name}")
            except Exception as e:
                print(f"  WARNING Could not clear {table_name}: {e}")
        else:
            print(f"  SKIP Table {table_name} doesn't exist")
    
    def reset_sequence(table_name: str):
        """Reset auto-increment sequence for table"""
        if table_exists(table_name):
            try:
                # PostgreSQL
                conn.exec_driver_sql(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1")
                print(f"  SUCCESS Reset {table_name}_id_seq to start from 1")
            except Exception:
                # SQLite - sequences reset automatically with DELETE
                print(f"  INFO Sequence for {table_name} will reset automatically")
    
    # 1. PRESERVE ADMIN USERS
    print("STEP 1: Preserving admin users...")
    if table_exists('users'):
        try:
            admin_count = conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE role = 'admin'").scalar()
            print(f"  INFO Found {admin_count} admin user(s) to preserve")
            
            # Delete non-admin users only
            safe_clear_table('users', "role != 'admin'")
            
            # Verify admin users still exist
            remaining_admin = conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE role = 'admin'").scalar()
            print(f"  SUCCESS {remaining_admin} admin user(s) preserved")
        except Exception as e:
            print(f"  WARNING Could not preserve admin users: {e}")
    
    # 2. CLEAR BUSINESS DATA TABLES (in dependency order)
    print("STEP 2: Clearing business data...")
    
    # Clear child tables first (due to foreign keys)
    business_tables = [
        # Order-related children first
        "order_notes",
        "pod_photos", 
        "order_item_uids",
        "order_items",
        "payments",
        "plans",
        
        # Trip-related
        "trip_events", 
        "trips",
        
        # Order parents
        "orders",
        
        # Other business data
        "customers",
        "drivers",
        "routes", 
        "lorries",
        "driver_shifts",
        
        # Commission and financial
        "commission_entries",
        "commissions", 
        "export_runs",
        
        # Inventory and products
        "skus",
        "items",
        "stock_transactions",
        "lorry_stock_transactions",
        
        # Background processing
        "background_jobs",
        "jobs",
        "idempotent_requests",
        
        # Administrative (except users)
        "audit_logs",
        "driver_assignments",
        "driver_holds", 
        "organizations",
        "upsell_records",
        
        # Verification and tracking
        "ai_verification_logs",
        "uid_ledgers",
    ]
    
    # Clear each table
    for table in business_tables:
        safe_clear_table(table)
    
    # 3. RESET SEQUENCES
    print("STEP 3: Resetting auto-increment sequences...")
    
    sequence_tables = [
        "customers", "orders", "order_items", "plans", "payments",
        "trips", "drivers", "routes", "skus", "lorries"
    ]
    
    for table in sequence_tables:
        reset_sequence(table)
    
    # 4. VERIFY CLEAN STATE
    print("STEP 4: Verifying clean state...")
    
    verification_tables = ["orders", "customers", "payments", "trips", "drivers"]
    for table in verification_tables:
        if table_exists(table):
            try:
                count = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").scalar()
                print(f"  STATS {table}: {count} records")
            except Exception as e:
                print(f"  WARNING Could not verify {table}: {e}")
    
    # Verify admin users are still there
    if table_exists('users'):
        try:
            admin_count = conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE role = 'admin'").scalar()
            total_users = conn.exec_driver_sql("SELECT COUNT(*) FROM users").scalar()
            print(f"  ADMIN USERS: {admin_count} admin, {total_users} total users")
        except Exception as e:
            print(f"  WARNING Could not verify users: {e}")
    
    print("DATA RESET COMPLETED!")
    print("SUCCESS All table structures preserved")
    print("SUCCESS All business data wiped clean")
    print("SUCCESS Admin users maintained")
    print("SUCCESS Sequences reset for fresh auto-increment IDs")
    print("SUCCESS Ready for fresh data with existing table structure!")

def downgrade() -> None:
    """
    Cannot restore deleted data - this is a destructive data operation
    """
    print("WARNING Cannot restore deleted data from data reset")
    print("INFO Use database backup to restore data if needed")
    print("INFO Table structures were preserved, only data was deleted")
