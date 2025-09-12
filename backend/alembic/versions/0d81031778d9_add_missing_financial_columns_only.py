
#!/usr/bin/env python


"""add_missing_financial_columns_only

Revision ID: 0d81031778d9
Revises: 6f93d3e848a6
Create Date: 2025-09-12 08:19:37.472425

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0d81031778d9'
down_revision = '6f93d3e848a6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Only add subtotal column since the error specifically mentioned it
    # Use IF NOT EXISTS-like approach with try/except
    connection = op.get_bind()
    
    # Check if subtotal column exists
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'subtotal'
    """))
    
    if not result.fetchone():
        op.add_column('orders', sa.Column('subtotal', sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))
    
    # Check and add other potentially missing columns one by one
    columns_to_check = [
        'discount', 'delivery_fee', 'return_delivery_fee', 
        'penalty_fee', 'balance'
    ]
    
    for col_name in columns_to_check:
        result = connection.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = '{col_name}'
        """))
        
        if not result.fetchone():
            op.add_column('orders', sa.Column(col_name, sa.Numeric(12, 2), default=sa.text("0.00"), nullable=False))

def downgrade() -> None:
    # Drop columns that were added (in reverse order)
    columns_to_drop = [
        'balance', 'penalty_fee', 'return_delivery_fee', 
        'delivery_fee', 'discount', 'subtotal'
    ]
    
    connection = op.get_bind()
    
    for col_name in columns_to_drop:
        result = connection.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = '{col_name}'
        """))
        
        if result.fetchone():
            op.drop_column('orders', col_name)
