"""add closure_reason to driver_shifts

Revision ID: add_closure_reason_001
Revises: 
Create Date: 2025-09-13 01:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_closure_reason_001'
down_revision = 'ff3a4b5c6d7e'  # create_lorry_stock_transactions
branch_labels = None
depends_on = None


def upgrade():
    # Add closure_reason column to driver_shifts table
    op.add_column('driver_shifts', sa.Column('closure_reason', sa.Text(), nullable=True))


def downgrade():
    # Remove closure_reason column from driver_shifts table
    op.drop_column('driver_shifts', 'closure_reason')