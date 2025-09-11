
#!/usr/bin/env python


"""create_essential_tables_real

Revision ID: a10b52e31a1b
Revises: 20250911_ai_verification_log
Create Date: 2025-09-11 21:28:10.444830

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a10b52e31a1b'
down_revision = '20250911_ai_verification_log'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create essential tables for OrderOps application"""
    
    # Create users table first (referenced by others)
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create drivers table
    op.create_table('drivers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('firebase_uid', sa.String(length=128), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('firebase_uid')
    )
    
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='NEW'),
        sa.Column('type', sa.String(length=20), nullable=False, default='OUTRIGHT'),
        sa.Column('total', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('paid_amount', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('delivery_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Create routes table
    op.create_table('routes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create trips table
    op.create_table('trips',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('driver_id_2', sa.Integer(), nullable=True),
        sa.Column('route_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='ASSIGNED'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pod_photo_urls', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['driver_id_2'], ['drivers.id']),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create driver_shifts table  
    op.create_table('driver_shifts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('clock_in_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('clock_out_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clock_in_lat', sa.Float(), nullable=False),
        sa.Column('clock_in_lng', sa.Float(), nullable=False),
        sa.Column('clock_in_location_name', sa.String(length=200), nullable=True),
        sa.Column('clock_out_lat', sa.Float(), nullable=True),
        sa.Column('clock_out_lng', sa.Float(), nullable=True),
        sa.Column('clock_out_location_name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='ACTIVE'),
        sa.Column('is_outstation', sa.Boolean(), nullable=False, default=False),
        sa.Column('outstation_allowance_amount', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_drivers_firebase_uid', 'drivers', ['firebase_uid'])
    op.create_index('ix_orders_code', 'orders', ['code'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_customer_id', 'orders', ['customer_id'])
    op.create_index('ix_trips_order_id', 'trips', ['order_id'])
    op.create_index('ix_trips_driver_id', 'trips', ['driver_id'])
    op.create_index('ix_trips_status', 'trips', ['status'])
    op.create_index('ix_driver_shifts_driver_id', 'driver_shifts', ['driver_id'])
    op.create_index('ix_driver_shifts_status', 'driver_shifts', ['status'])
    
    print("✅ Created essential tables: users, customers, drivers, orders, routes, trips, driver_shifts")


def downgrade() -> None:
    """Drop essential tables"""
    op.drop_table('driver_shifts')
    op.drop_table('trips') 
    op.drop_table('orders')
    op.drop_table('routes')
    op.drop_table('drivers')
    op.drop_table('customers')
    op.drop_table('users')
    print("✅ Dropped essential tables")
