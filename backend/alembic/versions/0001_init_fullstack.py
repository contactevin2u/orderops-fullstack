"""init fullstack tables

Revision ID: 0001_init_fullstack
Revises: 
Create Date: 2025-08-18 00:00:00
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_init_fullstack'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('customers',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('map_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_customers_phone', 'customers', ['phone'])

    op.create_table('orders',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='NEW'),
        sa.Column('customer_id', sa.BigInteger(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('discount', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('delivery_fee', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('return_delivery_fee', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('penalty_fee', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('paid_amount', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('balance', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_orders_code', 'orders', ['code'], unique=True)

    op.create_table('order_items',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('item_type', sa.String(length=20), nullable=False),
        sa.Column('qty', sa.Numeric(12,0), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('line_total', sa.Numeric(12,2), nullable=False, server_default='0'),
    )

    op.create_table('plans',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('months', sa.Numeric(12,0), nullable=True),
        sa.Column('monthly_amount', sa.Numeric(12,2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
    )

    op.create_table('payments',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12,2), nullable=False),
        sa.Column('method', sa.String(length=30), nullable=True),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=False, server_default='ORDER'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='POSTED'),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_payments_order', 'payments', ['order_id'])

    op.create_table('jobs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='queued'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_jobs_status_id', 'jobs', ['status','id'])

def downgrade() -> None:
    op.drop_index('ix_jobs_status_id', table_name='jobs')
    op.drop_table('jobs')
    op.drop_index('ix_payments_order', table_name='payments')
    op.drop_table('payments')
    op.drop_table('plans')
    op.drop_table('order_items')
    op.drop_index('ix_orders_code', table_name='orders')
    op.drop_table('orders')
    op.drop_index('ix_customers_phone', table_name='customers')
    op.drop_table('customers')
