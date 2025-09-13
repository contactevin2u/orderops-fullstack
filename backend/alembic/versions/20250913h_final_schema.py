"""final comprehensive schema - clean rebuild after CASCADE

Revision ID: 20250913h_final_schema
Revises: 20250913g_simple_cascade
Create Date: 2025-09-13 20:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250913h_final_schema'
down_revision = '20250913g_simple_cascade'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Final comprehensive clean schema implementation after CASCADE cleanup
    This creates all the good features from our 40+ commits in one clean migration
    """
    print("🏗️  Building final comprehensive schema after CASCADE cleanup...")
    
    # 1. CORE BUSINESS TABLES
    print("📋 Creating core business tables...")
    
    # Customers table
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
    
    # Orders table with proper idempotency
    op.create_table('orders',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('type', sa.String(length=20), nullable=False),  # OUTRIGHT|INSTALLMENT|RENTAL|MIXED
        sa.Column('status', sa.String(length=20), nullable=False, default='NEW'),  # NEW|ACTIVE|RETURNED|CANCELLED|COMPLETED
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
        
        # IDEMPOTENCY - Proper implementation with partial unique index
        sa.Column('idempotency_key', sa.String(length=255), nullable=True, index=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Partial unique index for non-null idempotency keys (elegant solution!)
    op.execute("""
        CREATE UNIQUE INDEX ux_orders_idempotency_key 
        ON orders (idempotency_key) 
        WHERE idempotency_key IS NOT NULL
    """)
    
    # Order Items table with proper relationship
    op.create_table('order_items',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),  # BED|WHEELCHAIR|OXYGEN|ACCESSORY
        sa.Column('item_type', sa.String(length=20), nullable=False),  # OUTRIGHT|INSTALLMENT|RENTAL|FEE
        sa.Column('qty', sa.Numeric(12, 0), default=1, nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('line_total', sa.Numeric(12, 2), default=0, nullable=False),
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    
    # Plans table with proper constraints and timestamps
    op.create_table('plans',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_type', sa.String(length=20), nullable=False),  # RENTAL|INSTALLMENT
        sa.Column('start_date', sa.Date(), nullable=True),  # Nullable to fix previous issues
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('months', sa.Integer(), nullable=True),  # For installment
        sa.Column('monthly_amount', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('upfront_billed_amount', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('status', sa.String(length=20), default='ACTIVE', nullable=False),  # ACTIVE|CANCELLED|COMPLETED
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Unique constraint: one plan type per order (prevents duplicates)
    op.create_unique_constraint('ux_plans_order_type', 'plans', ['order_id', 'plan_type'])
    
    # Payments table with idempotency  
    op.create_table('payments',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('method', sa.String(length=30), nullable=True),  # cash/transfer/cheque/etc
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=20), default='ORDER', nullable=False),  # ORDER|RENTAL|INSTALLMENT|PENALTY|DELIVERY|BUYBACK
        sa.Column('status', sa.String(length=20), default='POSTED', nullable=False),  # POSTED|VOIDED
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('export_run_id', sa.String(length=40), nullable=True),
        sa.Column('exported_at', sa.DateTime(timezone=True), nullable=True),
        
        # IDEMPOTENCY for payments
        sa.Column('idempotency_key', sa.String(length=255), nullable=True, index=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Partial unique index for payments idempotency
    op.execute("""
        CREATE UNIQUE INDEX ux_payments_idempotency_key
        ON payments (idempotency_key)
        WHERE idempotency_key IS NOT NULL  
    """)
    
    print("✅ Core business tables created with proper idempotency!")
    
    # 2. DRIVER AND OPERATIONAL TABLES
    print("🚛 Creating driver and operational tables...")
    
    # Drivers table
    op.create_table('drivers',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('license_number', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), default='ACTIVE', nullable=False),  # ACTIVE|INACTIVE|SUSPENDED
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_drivers_name', 'drivers', ['name'])
    op.create_index('ix_drivers_phone', 'drivers', ['phone'])
    
    # Routes table
    op.create_table('routes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Trips table with PROPER state management (this was a big fix!)
    op.create_table('trips',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('route_id', sa.BigInteger(), sa.ForeignKey('routes.id'), nullable=True),
        sa.Column('status', sa.String(length=20), default='ASSIGNED', nullable=False),  # ASSIGNED|IN_TRANSIT|ON_SITE|COMPLETED|CANCELLED|ON_HOLD
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_trips_order_id', 'trips', ['order_id'])
    op.create_index('ix_trips_driver_id', 'trips', ['driver_id'])
    
    # CRITICAL: Prevent multiple active trips per (order_id, driver_id) - this was the big business issue!
    op.execute("""
        CREATE UNIQUE INDEX ux_trips_order_driver_active
        ON trips (order_id, driver_id)
        WHERE status IN ('ASSIGNED', 'IN_TRANSIT', 'ON_SITE', 'ON_HOLD')
    """)
    
    print("✅ Driver and trip tables created with proper state management!")
    
    # 3. SUPPORTING TABLES
    print("📦 Creating supporting tables...")
    
    # Order Notes table (this was needed for driver API)
    op.create_table('order_notes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('note_type', sa.String(length=30), default='GENERAL', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_order_notes_order_id', 'order_notes', ['order_id'])
    
    # POD Photos table (proof of delivery)
    op.create_table('pod_photos',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_pod_photos_order_id', 'pod_photos', ['order_id'])
    op.create_index('ix_pod_photos_driver_id', 'pod_photos', ['driver_id'])
    
    # Unique constraint: prevent duplicate photos for same order/url
    op.execute("""
        CREATE UNIQUE INDEX ux_pod_photos_order_url
        ON pod_photos(order_id, url)
    """)
    
    # SKUs table for inventory
    op.create_table('skus',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('sku', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('item_type', sa.String(length=20), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('status', sa.String(length=20), default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    print("✅ Supporting tables created!")
    
    # 4. IDEMPOTENCY SUPPORT TABLE  
    print("🔒 Creating idempotency support infrastructure...")
    
    # Idempotent requests table for complex operations
    op.create_table('idempotent_requests',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=True),  # Result reference
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    print("✅ Idempotency infrastructure created!")
    
    print("🎉 Final comprehensive schema completed successfully!")
    print("📋 All the good features from 40+ commits implemented cleanly!")
    print("🚀 Ready for production use with clean, maintainable schema!")

def downgrade() -> None:
    """Drop all tables created in this final schema migration"""
    print("🗑️  Rolling back final comprehensive schema...")
    
    # Drop in reverse dependency order
    tables = [
        'idempotent_requests',
        'pod_photos', 
        'order_notes',
        'skus',
        'trips',
        'routes', 
        'drivers',
        'payments',
        'plans',
        'order_items', 
        'orders',
        'customers',
    ]
    
    for table in tables:
        op.drop_table(table)