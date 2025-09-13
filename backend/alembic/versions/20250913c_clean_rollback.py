"""clean rollback migration - undo changes from reverted commits

Revision ID: 20250913c_clean_rollback
Revises: 20250913b_closure_backfill
Create Date: 2025-09-13 18:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250913c_clean_rollback'
down_revision = '20250913b_closure_backfill'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Clean rollback migration - undo all changes from reverted commits
    This brings the database back to a state compatible with commit bcd51a1
    """
    print("🧹 Starting clean rollback migration...")
    
    # Get database connection
    conn = op.get_bind()
    
    # 1. Remove idempotency-related columns and constraints if they exist
    print("Removing idempotency features...")
    
    # Drop partial unique indexes for idempotency keys
    op.execute("DROP INDEX IF EXISTS ux_orders_idempotency_key")
    op.execute("DROP INDEX IF EXISTS ux_payments_idempotency_key")
    
    # Check and remove idempotency_key columns
    orders_has_idem = conn.exec_driver_sql("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'orders' AND column_name = 'idempotency_key'
    """).first()
    
    if orders_has_idem:
        print("Removing orders.idempotency_key column...")
        op.drop_column("orders", "idempotency_key")
    
    payments_has_idem = conn.exec_driver_sql("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'payments' AND column_name = 'idempotency_key'
    """).first()
    
    if payments_has_idem:
        print("Removing payments.idempotency_key column...")
        op.drop_column("payments", "idempotency_key")
    
    # 2. Remove new tables that were added after bcd51a1
    print("Removing new tables...")
    
    # Check and remove order_notes table
    order_notes_exists = conn.exec_driver_sql("""
        SELECT to_regclass('public.order_notes') IS NOT NULL
    """).scalar()
    
    if order_notes_exists:
        print("Dropping order_notes table...")
        op.execute("DROP INDEX IF EXISTS ix_order_notes_order_id")
        op.drop_table("order_notes")
    
    # Check and remove pod_photos table
    pod_photos_exists = conn.exec_driver_sql("""
        SELECT to_regclass('public.pod_photos') IS NOT NULL
    """).scalar()
    
    if pod_photos_exists:
        print("Dropping pod_photos table...")
        op.execute("DROP INDEX IF EXISTS ux_pod_photos_order_url")
        op.execute("DROP INDEX IF EXISTS ix_pod_photos_order_id")
        op.execute("DROP INDEX IF EXISTS ix_pod_photos_driver_id")
        op.drop_table("pod_photos")
    
    # 3. Remove unique constraints that were added
    print("Removing added constraints...")
    
    # Remove plans unique constraint if it exists
    plans_constraint_exists = conn.exec_driver_sql("""
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'plans' AND constraint_name = 'ux_plans_order_type'
    """).fetchone()
    
    if plans_constraint_exists:
        print("Dropping plans unique constraint...")
        try:
            op.drop_constraint("ux_plans_order_type", "plans", type_="unique")
        except Exception as e:
            print(f"Note: Could not drop plans constraint: {e}")
    
    # 4. Remove trip active state constraints
    print("Removing trip active state constraints...")
    op.execute("DROP INDEX IF EXISTS ux_trips_order_driver_active")
    op.execute("DROP INDEX IF EXISTS ix_trips_active_unique")
    op.execute("DROP INDEX IF EXISTS ux_trips_active")
    
    # 5. Remove plan timestamp columns if they were added
    print("Checking plan table changes...")
    
    plan_end_date_exists = conn.exec_driver_sql("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'plans' AND column_name = 'end_date'
    """).first()
    
    if plan_end_date_exists:
        print("Removing plans.end_date column...")
        op.drop_column("plans", "end_date")
    
    plan_created_at_exists = conn.exec_driver_sql("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'plans' AND column_name = 'created_at'
    """).first()
    
    if plan_created_at_exists:
        print("Removing plans.created_at column...")
        op.drop_column("plans", "created_at")
    
    plan_updated_at_exists = conn.exec_driver_sql("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'plans' AND column_name = 'updated_at'
    """).first()
    
    if plan_updated_at_exists:
        print("Removing plans.updated_at column...")
        op.drop_column("plans", "updated_at")
    
    # 6. Clean up any background_jobs table
    bg_jobs_exists = conn.exec_driver_sql("""
        SELECT to_regclass('public.background_jobs') IS NOT NULL
    """).scalar()
    
    if bg_jobs_exists:
        print("Dropping background_jobs table...")
        op.execute("DROP INDEX IF EXISTS ix_background_jobs_status")
        op.execute("DROP INDEX IF EXISTS ix_background_jobs_job_type")  
        op.execute("DROP INDEX IF EXISTS ix_background_jobs_created_at")
        op.drop_table("background_jobs")
    
    print("✅ Clean rollback migration completed successfully!")
    print("Database is now compatible with commit bcd51a1")

def downgrade() -> None:
    """
    This migration is a one-way cleanup - downgrade would restore the complex state
    which we're trying to simplify. Not implemented to avoid re-complexity.
    """
    print("⚠️  Downgrade not implemented - this is a cleanup migration")
    print("To restore features, use proper forward migrations")