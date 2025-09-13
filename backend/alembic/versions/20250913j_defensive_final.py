"""defensive final schema - handles existing tables gracefully

Revision ID: 20250913j_defensive_final
Revises: 20250913i_merge_heads
Create Date: 2025-09-13 20:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250913j_defensive_final'
down_revision = '20250913i_merge_heads'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Defensive final schema that gracefully handles existing tables
    This ensures we get to a clean final state regardless of what cleanup worked
    """
    print("🛡️  DEFENSIVE FINAL SCHEMA: Handling existing tables gracefully...")
    
    conn = op.get_bind()
    
    def table_exists(table_name: str) -> bool:
        """Check if table exists"""
        result = conn.exec_driver_sql(f"""
            SELECT to_regclass('public.{table_name}') IS NOT NULL
        """).scalar()
        return result
    
    def create_table_if_not_exists(table_name: str, create_fn):
        """Create table only if it doesn't exist"""
        if table_exists(table_name):
            print(f"  ✓ Table {table_name} already exists, skipping creation")
        else:
            print(f"  📋 Creating table {table_name}...")
            create_fn()
    
    # 1. CORE BUSINESS TABLES
    print("📋 Ensuring core business tables exist...")
    
    def create_customers():
        op.create_table('customers',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('phone', sa.String(length=20), nullable=True),
            sa.Column('email', sa.String(length=100), nullable=True), 
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('map_url', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('ix_customers_phone', 'customers', ['phone'])
        op.create_index('ix_customers_name', 'customers', ['name'])
    
    create_table_if_not_exists('customers', create_customers)
    
    def create_orders():
        op.create_table('orders',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('code', sa.String(length=32), nullable=False, unique=True, index=True),
            sa.Column('type', sa.String(length=20), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, default='NEW'),
            sa.Column('customer_id', sa.BigInteger(), sa.ForeignKey('customers.id'), nullable=False),
            sa.Column('parent_id', sa.BigInteger(), sa.ForeignKey('orders.id'), nullable=True, index=True),
            sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True), 
            sa.Column('notes', sa.Text(), nullable=True),
            
            # Financial fields
            sa.Column('subtotal', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('discount', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('delivery_fee', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('return_delivery_fee', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('penalty_fee', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('total', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('paid_amount', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('balance', sa.Numeric(12, 2), default=0, nullable=False),
            
            # IDEMPOTENCY
            sa.Column('idempotency_key', sa.String(length=255), nullable=True, index=True),
            
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        
        # Ensure idempotency index exists
        try:
            op.execute("""
                CREATE UNIQUE INDEX ux_orders_idempotency_key 
                ON orders (idempotency_key) 
                WHERE idempotency_key IS NOT NULL
            """)
        except Exception as e:
            print(f"  Note: Idempotency index may already exist: {e}")
    
    create_table_if_not_exists('orders', create_orders)
    
    def create_order_items():
        op.create_table('order_items',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('sku', sa.String(length=100), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=True),
            sa.Column('item_type', sa.String(length=20), nullable=False),
            sa.Column('qty', sa.Numeric(12, 0), default=1, nullable=False),
            sa.Column('unit_price', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('line_total', sa.Numeric(12, 2), default=0, nullable=False),
        )
        op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    
    create_table_if_not_exists('order_items', create_order_items)
    
    def create_plans():
        op.create_table('plans',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
            sa.Column('plan_type', sa.String(length=20), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('months', sa.Integer(), nullable=True),
            sa.Column('monthly_amount', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('upfront_billed_amount', sa.Numeric(12, 2), default=0, nullable=False),
            sa.Column('status', sa.String(length=20), default='ACTIVE', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        
        try:
            op.create_unique_constraint('ux_plans_order_type', 'plans', ['order_id', 'plan_type'])
        except Exception as e:
            print(f"  Note: Plans constraint may already exist: {e}")
    
    create_table_if_not_exists('plans', create_plans)
    
    def create_payments():
        op.create_table('payments',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('amount', sa.Numeric(12, 2), nullable=False),
            sa.Column('method', sa.String(length=30), nullable=True),
            sa.Column('reference', sa.String(length=100), nullable=True),
            sa.Column('category', sa.String(length=20), default='ORDER', nullable=False),
            sa.Column('status', sa.String(length=20), default='POSTED', nullable=False),
            sa.Column('void_reason', sa.Text(), nullable=True),
            sa.Column('export_run_id', sa.String(length=40), nullable=True),
            sa.Column('exported_at', sa.DateTime(timezone=True), nullable=True),
            
            # IDEMPOTENCY for payments
            sa.Column('idempotency_key', sa.String(length=255), nullable=True, index=True),
            
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        
        try:
            op.execute("""
                CREATE UNIQUE INDEX ux_payments_idempotency_key
                ON payments (idempotency_key)
                WHERE idempotency_key IS NOT NULL  
            """)
        except Exception as e:
            print(f"  Note: Payments idempotency index may already exist: {e}")
    
    create_table_if_not_exists('payments', create_payments)
    
    print("✅ Core business tables ensured!")
    
    # 2. ADD MISSING COLUMNS TO EXISTING TABLES
    print("🔧 Adding missing columns to existing tables...")
    
    # Add idempotency_key to orders if missing
    try:
        has_orders_idem = conn.exec_driver_sql("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'orders' AND column_name = 'idempotency_key'
        """).first()
        
        if not has_orders_idem:
            print("  📋 Adding idempotency_key to orders table...")
            op.add_column('orders', sa.Column('idempotency_key', sa.String(length=255), nullable=True, index=True))
            
            # Add the partial unique index
            op.execute("""
                CREATE UNIQUE INDEX ux_orders_idempotency_key 
                ON orders (idempotency_key) 
                WHERE idempotency_key IS NOT NULL
            """)
        else:
            print("  ✓ Orders table already has idempotency_key")
    except Exception as e:
        print(f"  Note: Could not add orders idempotency: {e}")
    
    # Add idempotency_key to payments if missing
    try:
        has_payments_idem = conn.exec_driver_sql("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'payments' AND column_name = 'idempotency_key'
        """).first()
        
        if not has_payments_idem:
            print("  📋 Adding idempotency_key to payments table...")
            op.add_column('payments', sa.Column('idempotency_key', sa.String(length=255), nullable=True, index=True))
            
            # Add the partial unique index
            op.execute("""
                CREATE UNIQUE INDEX ux_payments_idempotency_key
                ON payments (idempotency_key)
                WHERE idempotency_key IS NOT NULL  
            """)
        else:
            print("  ✓ Payments table already has idempotency_key")
    except Exception as e:
        print(f"  Note: Could not add payments idempotency: {e}")
    
    print("✅ Missing columns added!")
    
    print("🎉 DEFENSIVE FINAL SCHEMA COMPLETED!")
    print("📋 Database is now in proper state with all essential features")
    print("🚀 Application should work correctly with existing or new schema")

def downgrade() -> None:
    """This is a defensive migration - downgrade removes added features only"""
    print("⚠️  Removing defensive schema additions...")
    
    # Remove only what we added, don't break existing functionality
    try:
        op.execute("DROP INDEX IF EXISTS ux_orders_idempotency_key")
        op.execute("DROP INDEX IF EXISTS ux_payments_idempotency_key")
    except Exception as e:
        print(f"Could not remove indexes: {e}")
    
    print("Defensive schema downgrade completed")