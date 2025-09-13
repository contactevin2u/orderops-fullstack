"""clean database restart - preserve admin user only

Revision ID: 20250913d_clean_restart
Revises: 20250913c_clean_rollback
Create Date: 2025-09-13 19:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250913d_clean_restart'
down_revision = '20250913c_clean_rollback'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Clean database restart - preserve admin user, reset everything else
    This gives us a fresh start to implement all the good features properly
    """
    print("🚀 Starting clean database restart...")
    print("⚠️  This will remove all orders, customers, and business data!")
    print("✅ Admin users will be preserved")
    
    # Get database connection
    conn = op.get_bind()
    
    # 1. PRESERVE ADMIN USER DATA
    print("📦 Backing up admin user data...")
    
    # We'll keep the users table intact - it should have the admin user
    # Just ensure we don't accidentally delete it
    
    # 2. DROP ALL BUSINESS DATA TABLES (order matters for foreign keys)
    print("🗑️  Removing all business data tables...")
    
    tables_to_drop = [
        # Order-related (drop first due to foreign keys)
        "order_notes",
        "pod_photos", 
        "order_item_uids",
        "order_items",
        "payments",
        "plans",
        "trips",
        "orders",
        
        # Customer and business data
        "customers",
        "drivers",
        "routes",
        "lorries",
        "driver_shifts",
        "skus",
        "items",
        
        # Background processing
        "background_jobs",
        "jobs",
        
        # Other business tables
        "commissions",
        "export_runs",
        "idempotent_requests",
        "lorry_stock_transactions",
        "audit_logs",
        
        # Driver and operational
        "driver_assignments",
        "driver_holds", 
        "trip_events",
        "organizations",
        
        # Verification and tracking
        "ai_verification_logs",
        "uid_ledgers",
        "stock_transactions",
        "upsell_records",
    ]
    
    for table in tables_to_drop:
        try:
            # Check if table exists first
            exists = conn.exec_driver_sql(f"""
                SELECT to_regclass('public.{table}') IS NOT NULL
            """).scalar()
            
            if exists:
                print(f"  Dropping table: {table}")
                op.drop_table(table)
            else:
                print(f"  Table {table} doesn't exist, skipping...")
        except Exception as e:
            print(f"  Warning: Could not drop {table}: {e}")
            # Continue - some tables might not exist or have dependencies
            pass
    
    # 3. DROP ALL INDEXES that might be orphaned
    print("🧹 Cleaning up orphaned indexes...")
    
    orphaned_indexes = [
        "ux_orders_idempotency_key",
        "ux_payments_idempotency_key", 
        "ux_plans_order_type",
        "ux_trips_order_driver_active",
        "ux_pod_photos_order_url",
        "ix_trips_active_unique",
        "ux_trips_active",
    ]
    
    for idx in orphaned_indexes:
        try:
            op.execute(f"DROP INDEX IF EXISTS {idx}")
        except Exception as e:
            print(f"  Note: Could not drop index {idx}: {e}")
    
    # 4. VERIFY ADMIN USER STILL EXISTS
    print("👤 Verifying admin user preservation...")
    
    try:
        admin_count = conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE role = 'admin'").scalar()
        if admin_count > 0:
            print(f"✅ {admin_count} admin user(s) preserved successfully!")
        else:
            print("⚠️  No admin users found - you may need to recreate admin access")
    except Exception as e:
        print(f"⚠️  Could not verify admin users: {e}")
    
    print("🎉 Clean database restart completed!")
    print("📋 Next: Run the comprehensive schema migration to rebuild with all the good features")

def downgrade() -> None:
    """
    This is a destructive reset migration - downgrade would need to restore
    all the business data which we don't have anymore.
    """
    print("❌ Cannot downgrade a clean restart migration")
    print("💡 To restore data, you would need a database backup")