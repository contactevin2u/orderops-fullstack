#!/usr/bin/env python

"""fix_plans_months_nullable

Revision ID: ff2a3b4c5d6e
Revises: ff1a2b3c4d5e
Create Date: 2025-09-12 03:21:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ff2a3b4c5d6e'
down_revision = 'ff1a2b3c4d5e'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Make months column nullable in plans table for RENTAL plans"""
    
    # Get database connection and inspector
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Check if plans table exists
    if inspector.has_table('plans'):
        try:
            # Alter the months column to allow NULL values
            # This is needed because RENTAL plans are perpetual (no fixed months)
            # while INSTALLMENT plans have fixed months
            op.alter_column('plans', 'months',
                           existing_type=sa.Integer(),
                           nullable=True)
            print("✅ Made plans.months column nullable for RENTAL plans")
        except Exception as e:
            print(f"⚠️ Could not alter plans.months column: {e}")
            print("   This may be because the column is already nullable")
    else:
        print("⚠️ plans table does not exist - this migration is not needed")

def downgrade() -> None:
    """Make months column non-nullable (will fail if null values exist)"""
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('plans'):
        # Note: This will fail if there are RENTAL plans with null months
        op.alter_column('plans', 'months',
                       existing_type=sa.Integer(),
                       nullable=False)
        print("✅ Made plans.months column non-nullable")