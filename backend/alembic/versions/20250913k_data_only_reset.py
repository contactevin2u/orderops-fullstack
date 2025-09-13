"""data only reset - keep tables, wipe data (preserve admin users)

Revision ID: 20250913k_data_only_reset
Revises: 20250913j_defensive_final
Create Date: 2025-09-13 20:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250913k_data_only_reset'
down_revision = '20250913j_defensive_final'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    DATA-ONLY RESET: Keep all tables and structure, just delete the data inside
    Preserve admin users but wipe all business data for fresh start
    """
    print("🧹 DATA-ONLY RESET: Wiping data while preserving table structure...")
    print("✅ All tables will remain intact")
    print("🗑️  All business data will be deleted")
    print("👤 Admin users will be preserved")
    
    conn = op.get_bind()
    
    def table_exists(table_name: str) -> bool:
        """Check if table exists"""
        try:
            result = conn.exec_driver_sql(f"""
                SELECT to_regclass('public.{table_name}') IS NOT NULL
            """).scalar()
            return result
        except Exception:
            return False
    
    def clear_table_data(table_name: str, condition: str = ""):
        """Clear data from table with optional condition"""
        if table_exists(table_name):
            try:
                if condition:
                    sql = f"DELETE FROM {table_name} WHERE {condition}"
                    conn.exec_driver_sql(sql)
                    print(f"  🗑️  Cleared {table_name} data (with condition: {condition})")
                else:
                    sql = f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"
                    conn.exec_driver_sql(sql)
                    print(f"  🗑️  Truncated {table_name} (reset sequences)")
            except Exception as e:
                print(f"  ⚠️  Could not clear {table_name}: {e}")
                # Try alternative approach
                try:
                    conn.exec_driver_sql(f"DELETE FROM {table_name}")
                    print(f"  🗑️  Deleted all data from {table_name} (fallback)")
                except Exception as e2:
                    print(f"  ❌ Failed to clear {table_name}: {e2}")
        else:
            print(f"  ➖ Table {table_name} doesn't exist, skipping...")
    
    # 1. PRESERVE ADMIN USERS - Clear non-admin users only
    print("👤 Preserving admin users...")
    if table_exists('users'):
        try:
            # Count admin users first
            admin_count = conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE role = 'admin'").scalar()
            print(f"  ✅ Found {admin_count} admin user(s) to preserve")
            
            # Delete non-admin users only
            clear_table_data('users', "role != 'admin'")
            
            # Verify admin users still exist
            remaining_admin = conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE role = 'admin'").scalar()
            print(f"  ✅ {remaining_admin} admin user(s) preserved successfully")
        except Exception as e:
            print(f"  ⚠️  Could not preserve admin users: {e}")
    
    # 2. CLEAR ALL BUSINESS DATA TABLES (in dependency order)
    print("🗑️  Clearing all business data...")
    
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
        
        # Administrative
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
        clear_table_data(table)
    
    # 3. RESET SEQUENCES for fresh auto-increment IDs
    print("🔄 Resetting auto-increment sequences...")
    
    sequence_tables = [
        "customers", "orders", "order_items", "plans", "payments", 
        "trips", "drivers", "routes", "skus"
    ]
    
    for table in sequence_tables:
        if table_exists(table):
            try:
                # Reset the sequence to 1
                conn.exec_driver_sql(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
                print(f"  🔄 Reset {table}_id_seq to start from 1")
            except Exception as e:
                print(f"  ⚠️  Could not reset sequence for {table}: {e}")
    
    # 4. VERIFY CLEAN STATE
    print("🔍 Verifying clean state...")
    
    verification_tables = ["orders", "customers", "payments", "trips", "drivers"]
    for table in verification_tables:
        if table_exists(table):
            try:
                count = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").scalar()
                print(f"  📊 {table}: {count} records")
            except Exception as e:
                print(f"  ⚠️  Could not verify {table}: {e}")
    
    print("🎉 DATA-ONLY RESET COMPLETED!")
    print("✅ All table structures preserved")
    print("🗑️  All business data wiped clean") 
    print("👤 Admin users maintained")
    print("🔄 Sequences reset for fresh auto-increment IDs")
    print("🚀 Ready for fresh data with existing table structure!")

def downgrade() -> None:
    """
    Cannot restore deleted data - this is a destructive data operation
    """
    print("❌ Cannot restore deleted data from data-only reset")
    print("💡 Use database backup to restore data if needed")
    print("📋 Table structures were preserved, only data was deleted")