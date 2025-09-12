
#!/usr/bin/env python


"""add_parent_id_to_orders

Revision ID: b29ca0588c22
Revises: cb9262d36f15
Create Date: 2025-09-12 08:08:08.962144

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b29ca0588c22'
down_revision = 'cb9262d36f15'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add parent_id column to orders table
    op.add_column('orders', sa.Column('parent_id', sa.BigInteger(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_orders_parent_id_orders', 'orders', 'orders', 
        ['parent_id'], ['id']
    )
    
    # Create index on parent_id
    op.create_index('ix_orders_parent_id', 'orders', ['parent_id'])

def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_orders_parent_id', 'orders')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_orders_parent_id_orders', 'orders', type_='foreignkey')
    
    # Drop column
    op.drop_column('orders', 'parent_id')
