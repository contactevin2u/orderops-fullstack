#!/usr/bin/env python

"""create_lorry_stock_transactions

Revision ID: ff3a4b5c6d7e
Revises: ff2a3b4c5d6e
Create Date: 2025-09-12 05:35:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ff3a4b5c6d7e'
down_revision = 'ff2a3b4c5d6e'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create lorry_stock_transactions table for lorry inventory management"""
    
    # Get database connection and inspector
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Create lorry_stock_transactions table if it doesn't exist
    if not inspector.has_table('lorry_stock_transactions'):
        op.create_table('lorry_stock_transactions',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('lorry_id', sa.String(length=50), nullable=False),
            sa.Column('action', sa.String(length=20), nullable=False),
            sa.Column('uid', sa.String(length=100), nullable=False),
            sa.Column('sku_id', sa.Integer(), nullable=True),
            sa.Column('order_id', sa.Integer(), nullable=True),
            sa.Column('driver_id', sa.Integer(), nullable=True),
            sa.Column('admin_user_id', sa.Integer(), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
            sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
            sa.ForeignKeyConstraint(['admin_user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for better performance
        op.create_index('ix_lorry_stock_transactions_lorry_id', 'lorry_stock_transactions', ['lorry_id'])
        op.create_index('ix_lorry_stock_transactions_uid', 'lorry_stock_transactions', ['uid'])
        op.create_index('ix_lorry_stock_transactions_sku_id', 'lorry_stock_transactions', ['sku_id'])
        op.create_index('ix_lorry_stock_transactions_order_id', 'lorry_stock_transactions', ['order_id'])
        op.create_index('ix_lorry_stock_transactions_driver_id', 'lorry_stock_transactions', ['driver_id'])
        op.create_index('ix_lorry_stock_transactions_transaction_date', 'lorry_stock_transactions', ['transaction_date'])
        
        print("✅ Created lorry_stock_transactions table with indexes")
    else:
        print("✅ lorry_stock_transactions table already exists - skipping")

def downgrade() -> None:
    """Drop lorry_stock_transactions table"""
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('lorry_stock_transactions'):
        # Drop indexes first
        op.drop_index('ix_lorry_stock_transactions_transaction_date', 'lorry_stock_transactions')
        op.drop_index('ix_lorry_stock_transactions_driver_id', 'lorry_stock_transactions')
        op.drop_index('ix_lorry_stock_transactions_order_id', 'lorry_stock_transactions')
        op.drop_index('ix_lorry_stock_transactions_sku_id', 'lorry_stock_transactions')
        op.drop_index('ix_lorry_stock_transactions_uid', 'lorry_stock_transactions')
        op.drop_index('ix_lorry_stock_transactions_lorry_id', 'lorry_stock_transactions')
        
        # Drop table
        op.drop_table('lorry_stock_transactions')
        print("✅ Dropped lorry_stock_transactions table and indexes")