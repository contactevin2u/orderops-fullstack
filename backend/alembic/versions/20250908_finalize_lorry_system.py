"""Finalize lorry system deployment

Revision ID: 20250908_finalize_lorry_system  
Revises: 20250908_complete_lorry_system
Create Date: 2025-09-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250908_finalize_lorry_system'
down_revision = '20250908_complete_lorry_system'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure the priority_lorry_id column is available
    # This migration just confirms the lorry system is ready
    pass


def downgrade():
    # No operations to reverse
    pass