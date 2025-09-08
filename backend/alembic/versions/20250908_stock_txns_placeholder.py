"""Placeholder for deleted stock transactions migration

Revision ID: 20250908_stock_txns
Revises: 20250907_lorry_models
Create Date: 2025-09-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250908_stock_txns'
down_revision = '20250907_lorry_models'
branch_labels = None
depends_on = None


def upgrade():
    # This is a placeholder - the actual stock transactions table 
    # is created in 20250908_complete_lorry_system migration
    pass


def downgrade():
    # This is a placeholder - no operations to undo
    pass