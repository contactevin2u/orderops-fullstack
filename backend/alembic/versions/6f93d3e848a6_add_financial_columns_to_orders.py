
#!/usr/bin/env python


"""add_financial_columns_to_orders

Revision ID: 6f93d3e848a6
Revises: b0c0cd7260ed
Create Date: 2025-09-12 08:15:47.159713

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6f93d3e848a6'
down_revision = 'b0c0cd7260ed'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add financial columns to orders table
    op.add_column('orders', sa.Column('subtotal', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    op.add_column('orders', sa.Column('discount', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    op.add_column('orders', sa.Column('delivery_fee', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    op.add_column('orders', sa.Column('return_delivery_fee', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    op.add_column('orders', sa.Column('penalty_fee', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    op.add_column('orders', sa.Column('paid_amount', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    op.add_column('orders', sa.Column('balance', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))

def downgrade() -> None:
    # Drop financial columns from orders table
    op.drop_column('orders', 'balance')
    op.drop_column('orders', 'paid_amount')
    op.drop_column('orders', 'penalty_fee')
    op.drop_column('orders', 'return_delivery_fee')
    op.drop_column('orders', 'delivery_fee')
    op.drop_column('orders', 'discount')
    op.drop_column('orders', 'subtotal')
