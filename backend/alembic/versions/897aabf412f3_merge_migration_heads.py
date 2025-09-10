
#!/usr/bin/env python


"""Merge migration heads

Revision ID: 897aabf412f3
Revises: 20250910_stock_transactions, 6d2bfed744a6
Create Date: 2025-09-10 15:33:03.868754

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '897aabf412f3'
down_revision = ('20250910_stock_transactions', '6d2bfed744a6')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
