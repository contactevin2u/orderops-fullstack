
#!/usr/bin/env python


"""add_all_missing_tables

Revision ID: 3236997f2f3e
Revises: a10b52e31a1b
Create Date: 2025-09-11 21:32:00.867636

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3236997f2f3e'
down_revision = 'a10b52e31a1b'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add all missing critical tables for complete OrderOps functionality"""
    
    # Create order_items table (CRITICAL - order line items)
    op.create_table('order_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('item_type', sa.String(length=20), nullable=False),
        sa.Column('qty', sa.Numeric(12, 0), nullable=False, default=1),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create payments table (CRITICAL - payment tracking)
    op.create_table('payments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('method', sa.String(length=30), nullable=True),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=False, default='ORDER'),
        sa.Column('status', sa.String(length=20), nullable=False, default='POSTED'),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('export_run_id', sa.String(length=40), nullable=True),
        sa.Column('exported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    
    # Create sku table (CRITICAL - product catalog)
    op.create_table('sku',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('price', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create trip_events table (trip status history)
    op.create_table('trip_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create commission_entries table (driver commissions)
    op.create_table('commission_entries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='EARNED'),
        sa.Column('scheme', sa.String(length=50), nullable=True),
        sa.Column('rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('payment_method', sa.String(length=30), nullable=True),
        sa.Column('ai_verified', sa.Boolean(), nullable=True),
        sa.Column('cash_collection_required', sa.Boolean(), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create plans table (installment plans)
    op.create_table('plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('months', sa.Integer(), nullable=False),
        sa.Column('monthly_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create audit_logs table (system audit trail)
    op.create_table('audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.String(length=50), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create item table (physical items with UIDs)
    op.create_table('item',
        sa.Column('uid', sa.String(length=100), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='AVAILABLE'),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.PrimaryKeyConstraint('uid')
    )
    
    # Create driver_devices table (driver device registration)
    op.create_table('driver_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('firebase_token', sa.String(length=255), nullable=False),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create idempotent_requests table (API idempotency)
    op.create_table('idempotent_requests',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    
    # Create performance indexes
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_sku', 'order_items', ['sku'])
    op.create_index('ix_payments_order_id', 'payments', ['order_id'])
    op.create_index('ix_payments_date', 'payments', ['date'])
    op.create_index('ix_payments_method', 'payments', ['method'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_idempotency_key', 'payments', ['idempotency_key'])
    op.create_index('ix_sku_name', 'sku', ['name'])
    op.create_index('ix_sku_category', 'sku', ['category'])
    op.create_index('ix_trip_events_trip_id', 'trip_events', ['trip_id'])
    op.create_index('ix_trip_events_status', 'trip_events', ['status'])
    op.create_index('ix_commission_entries_trip_id', 'commission_entries', ['trip_id'])
    op.create_index('ix_commission_entries_driver_id', 'commission_entries', ['driver_id'])
    op.create_index('ix_commission_entries_status', 'commission_entries', ['status'])
    op.create_index('ix_plans_order_id', 'plans', ['order_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_item_sku_id', 'item', ['sku_id'])
    op.create_index('ix_item_status', 'item', ['status'])
    op.create_index('ix_driver_devices_driver_id', 'driver_devices', ['driver_id'])
    op.create_index('ix_driver_devices_firebase_token', 'driver_devices', ['firebase_token'])
    
    print("✅ Created ALL missing tables: order_items, payments, sku, trip_events, commission_entries, plans, audit_logs, item, driver_devices, idempotent_requests")


def downgrade() -> None:
    """Drop all the added tables"""
    op.drop_table('idempotent_requests')
    op.drop_table('driver_devices')
    op.drop_table('item')
    op.drop_table('audit_logs')
    op.drop_table('plans')
    op.drop_table('commission_entries')
    op.drop_table('trip_events')
    op.drop_table('sku')
    op.drop_table('payments')
    op.drop_table('order_items')
    print("✅ Dropped all added tables")
