"""Add base_warehouse column to drivers table

Revision ID: 20250905_add_driver_base_warehouse
Revises: f36d7abf49c7
Create Date: 2025-09-05 03:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250905_add_driver_base_warehouse'
down_revision = 'f36d7abf49c7'
branch_labels = None
depends_on = None

def upgrade():
    # Add base_warehouse column to drivers table
    op.add_column('drivers', sa.Column('base_warehouse', sa.String(length=20), nullable=False, server_default='BATU_CAVES'))

def downgrade():
    # Remove base_warehouse column from drivers table
    op.drop_column('drivers', 'base_warehouse')