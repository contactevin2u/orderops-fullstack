
#!/usr/bin/env python


"""merge_multiple_heads

Revision ID: b2e2139385dc
Revises: 20250905_add_driver_base_warehouse, a3c70e9437fe
Create Date: 2025-09-05 12:04:49.793773

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2e2139385dc'
down_revision = ('20250905_add_driver_base_warehouse', 'a3c70e9437fe')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
