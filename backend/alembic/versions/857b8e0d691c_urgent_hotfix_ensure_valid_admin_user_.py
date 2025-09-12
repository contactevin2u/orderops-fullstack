
#!/usr/bin/env python


"""urgent_hotfix_ensure_valid_admin_user_for_transactions

Revision ID: 857b8e0d691c
Revises: f0fbce482ef0
Create Date: 2025-09-12 20:39:58.841437

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '857b8e0d691c'
down_revision = 'f0fbce482ef0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This migration is no longer needed since admin_user_id is now nullable
    # Driver deliveries don't require admin authorization
    print("✅ Migration skipped - admin_user_id is now nullable for driver deliveries")
    pass

def downgrade() -> None:
    # No downgrade needed since this migration does nothing
    print("✅ Downgrade skipped - no changes were made")
    pass
