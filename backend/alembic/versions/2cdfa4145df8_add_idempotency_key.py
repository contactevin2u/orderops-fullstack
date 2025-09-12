
#!/usr/bin/env python


"""add_idempotency_key

Revision ID: 2cdfa4145df8
Revises: 0d81031778d9
Create Date: 2025-09-12 08:30:21.432332

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2cdfa4145df8'
down_revision = '0d81031778d9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if idempotency_key column exists before adding
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'idempotency_key'
    """))
    
    if not result.fetchone():
        op.add_column('orders', sa.Column('idempotency_key', sa.String(64), unique=True, nullable=True))
        op.create_index('ix_orders_idempotency_key', 'orders', ['idempotency_key'])

def downgrade() -> None:
    # Drop index and column if they exist
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'idempotency_key'
    """))
    
    if result.fetchone():
        op.drop_index('ix_orders_idempotency_key', 'orders')
        op.drop_column('orders', 'idempotency_key')
