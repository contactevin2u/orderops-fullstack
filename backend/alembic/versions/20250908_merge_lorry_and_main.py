"""Merge lorry system with main migration chain

Revision ID: 20250908_merge_lorry_and_main
Revises: 20250908_complete_lorry_system, 3c8b1c03e2ca
Create Date: 2025-09-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250908_merge_lorry_and_main'
down_revision = ('20250908_complete_lorry_system', '20250908_stock_txns', '3c8b1c03e2ca')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no operations needed
    pass


def downgrade():
    # This is a merge migration - no operations needed  
    pass