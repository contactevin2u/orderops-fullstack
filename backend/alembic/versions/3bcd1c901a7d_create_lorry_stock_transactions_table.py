
#!/usr/bin/env python


"""create_lorry_stock_transactions_table

Revision ID: 3bcd1c901a7d
Revises: 6d2bfed744a6
Create Date: 2025-09-09 10:44:26.686293

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3bcd1c901a7d'
down_revision = '6d2bfed744a6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create lorry_stock_transactions table
    op.create_table(
        'lorry_stock_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(50), nullable=False, index=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('uid', sa.String(100), nullable=False, index=True),
        sa.Column('sku_id', sa.Integer(), nullable=True, index=True),
        sa.Column('order_id', sa.Integer(), nullable=True, index=True),
        sa.Column('driver_id', sa.Integer(), nullable=True, index=True),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'])
    )

def downgrade() -> None:
    # Drop lorry_stock_transactions table
    op.drop_table('lorry_stock_transactions')
