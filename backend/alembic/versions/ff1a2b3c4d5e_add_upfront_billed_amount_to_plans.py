#!/usr/bin/env python

"""add_upfront_billed_amount_to_plans

Revision ID: ff1a2b3c4d5e  
Revises: f7e2c8b5a9d4
Create Date: 2025-09-12 02:51:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ff1a2b3c4d5e'
down_revision = 'f7e2c8b5a9d4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add upfront_billed_amount column to plans table if missing"""
    
    # Get database connection and inspector
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Check if plans table exists
    if inspector.has_table('plans'):
        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('plans')]
        
        # Add upfront_billed_amount column if it doesn't exist
        if 'upfront_billed_amount' not in columns:
            try:
                op.add_column('plans', 
                    sa.Column('upfront_billed_amount', sa.Numeric(12, 2), 
                             nullable=False, server_default='0.00'))
                print("✅ Added upfront_billed_amount column to plans table")
            except Exception as e:
                print(f"⚠️ Could not add upfront_billed_amount column: {e}")
        else:
            print("✅ upfront_billed_amount column already exists in plans table")
    else:
        # Create the entire plans table if it doesn't exist
        op.create_table('plans',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('plan_type', sa.String(length=20), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('months', sa.Integer(), nullable=True),
            sa.Column('monthly_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
            sa.Column('upfront_billed_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
            sa.PrimaryKeyConstraint('id')
        )
        print("✅ Created plans table with upfront_billed_amount column")

def downgrade() -> None:
    """Remove upfront_billed_amount column from plans table"""
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('plans'):
        columns = [col['name'] for col in inspector.get_columns('plans')]
        if 'upfront_billed_amount' in columns:
            op.drop_column('plans', 'upfront_billed_amount')
            print("✅ Removed upfront_billed_amount column from plans table")