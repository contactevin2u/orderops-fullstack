
#!/usr/bin/env python


"""add_returned_at_to_orders

Revision ID: b0c0cd7260ed
Revises: b29ca0588c22
Create Date: 2025-09-12 08:12:18.961359

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b0c0cd7260ed'
down_revision = 'b29ca0588c22'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add returned_at column to orders table
    op.add_column('orders', sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    # Drop returned_at column
    op.drop_column('orders', 'returned_at')
