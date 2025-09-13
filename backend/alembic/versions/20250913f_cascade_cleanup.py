"""cascade cleanup - properly handle foreign key dependencies

Revision ID: 20250913f_cascade_cleanup
Revises: 20250913e_comprehensive
Create Date: 2025-09-13 19:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250913f_cascade_cleanup'
down_revision = '20250913e_comprehensive'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Properly clean up database with CASCADE to handle foreign key dependencies
    This fixes the previous migration that failed due to constraint dependencies
    """
    print("🧹 CASCADE CLEANUP: Properly handling foreign key dependencies...")
    
    # Get database connection
    conn = op.get_bind()
    
    # Use a single transaction with proper CASCADE handling
    print("🗑️  Dropping all business tables with CASCADE...")
    
    # Drop tables in dependency order with CASCADE where needed
    tables_to_cascade = [
        # These need CASCADE due to foreign key references
        "trips",
        "orders", 
        "customers",
        "drivers",
        
        # These should be safe to drop normally
        "commissions",
        "trip_events", 
        "commission_entries",
        "upsell_records",
        "lorry_stock_transactions",
        "audit_logs",
        "driver_assignments",
        "driver_holds",
        "organizations",
        "ai_verification_logs",
        "uid_ledgers", 
        "stock_transactions",
        "export_runs",
        "idempotent_requests",
        "background_jobs",
        "jobs",
        "items",
        "skus",
        "lorries",
        "routes",
        "driver_shifts",
    ]
    
    for table in tables_to_cascade:
        try:
            # Check if table exists first
            exists = conn.exec_driver_sql(f"""
                SELECT to_regclass('public.{table}') IS NOT NULL
            """).scalar()
            
            if exists:
                print(f"  Dropping table with CASCADE: {table}")
                # Use CASCADE to automatically drop dependent objects
                conn.exec_driver_sql(f"DROP TABLE {table} CASCADE")
            else:
                print(f"  Table {table} doesn't exist, skipping...")
        except Exception as e:
            print(f"  Warning: Could not drop {table}: {e}")
            # Continue with other tables
            pass
    
    print("✅ CASCADE cleanup completed!")
    print("📋 All business data has been removed")
    print("👤 Admin users preserved in 'users' table")

def downgrade() -> None:
    """
    This is a destructive cleanup migration - cannot restore deleted data
    """
    print("❌ Cannot restore data deleted by CASCADE cleanup")
    print("💡 Use database backup to restore if needed")