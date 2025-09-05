
#!/usr/bin/env python


"""Add driver base warehouse

Revision ID: drv_base_wh
Revises: a3c70e9437fe
Create Date: 2025-09-05 13:00:12.000310

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'drv_base_wh'
down_revision = 'a3c70e9437fe'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add base_warehouse column to drivers table
    op.add_column('drivers', sa.Column('base_warehouse', sa.String(length=20), nullable=False, server_default='BATU_CAVES'))

def downgrade() -> None:
    # Remove base_warehouse column from drivers table
    op.drop_column('drivers', 'base_warehouse')
