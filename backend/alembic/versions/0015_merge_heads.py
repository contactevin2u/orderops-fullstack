
#!/usr/bin/env python


"""merge_heads

Revision ID: 59e27afac749
Revises: 0014_enhance_uid_system, drv_base_wh
Create Date: 2025-09-06 09:44:00.423184

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0015_merge_heads'
down_revision = ('0014_enhance_uid_system', 'drv_base_wh')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
