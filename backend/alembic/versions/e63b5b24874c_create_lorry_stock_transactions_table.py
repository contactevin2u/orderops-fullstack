
#!/usr/bin/env python


"""create_lorry_stock_transactions_table

Revision ID: e63b5b24874c
Revises: 6d2bfed744a6
Create Date: 2025-09-09 10:08:14.775800

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e63b5b24874c'
down_revision = '6d2bfed744a6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create lorry_stock_transactions table
    op.create_table(
        'lorry_stock_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(50), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('uid', sa.String(100), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_lorry_stock_transactions_lorry_id', 'lorry_stock_transactions', ['lorry_id'])
    op.create_index('ix_lorry_stock_transactions_uid', 'lorry_stock_transactions', ['uid'])
    op.create_index('ix_lorry_stock_transactions_sku_id', 'lorry_stock_transactions', ['sku_id'])
    op.create_index('ix_lorry_stock_transactions_order_id', 'lorry_stock_transactions', ['order_id'])
    op.create_index('ix_lorry_stock_transactions_driver_id', 'lorry_stock_transactions', ['driver_id'])
    op.create_index('ix_lorry_stock_transactions_transaction_date', 'lorry_stock_transactions', ['transaction_date'])
    
    # Add foreign key constraints
    op.create_foreign_key(None, 'lorry_stock_transactions', 'orders', ['order_id'], ['id'])
    op.create_foreign_key(None, 'lorry_stock_transactions', 'drivers', ['driver_id'], ['id'])
    op.create_foreign_key(None, 'lorry_stock_transactions', 'users', ['admin_user_id'], ['id'])

def downgrade() -> None:
    # Drop indexes and table
    op.drop_table('lorry_stock_transactions')
