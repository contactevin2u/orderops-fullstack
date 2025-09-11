
#!/usr/bin/env python


"""Merge driver holds and production heads

Revision ID: 8d6e613b90ed
Revises: 20250911_add_driver_holds, 897aabf412f3
Create Date: 2025-09-11 09:00:54.589919

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8d6e613b90ed'
down_revision = ('20250911_add_driver_holds', '897aabf412f3')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
