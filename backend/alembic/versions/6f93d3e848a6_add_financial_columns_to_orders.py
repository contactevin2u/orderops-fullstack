
#!/usr/bin/env python


"""add_financial_columns_to_orders

Revision ID: 6f93d3e848a6
Revises: b0c0cd7260ed
Create Date: 2025-09-12 08:15:47.159713

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6f93d3e848a6'
down_revision = 'b0c0cd7260ed'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This migration failed due to duplicate columns - converted to no-op
    # The actual column additions are handled by 0d81031778d9_add_missing_financial_columns_only
    pass

def downgrade() -> None:
    # No-op downgrade since upgrade does nothing
    pass
