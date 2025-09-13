"""merge multiple migration heads into single chain

Revision ID: 20250913i_merge_heads
Revises: 20250913d_clean_restart, 20250913f_cascade_cleanup, 20250913h_final_schema
Create Date: 2025-09-13 20:15:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250913i_merge_heads'
# Merge all three heads into one
down_revision = ('20250913d_clean_restart', '20250913f_cascade_cleanup', '20250913h_final_schema')
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Merge migration heads - no actual database changes needed
    This just consolidates the branched migration paths into a single head
    """
    print("🔄 Merging multiple migration heads into single chain...")
    print("✅ Migration heads successfully merged - no database changes needed")
    print("📋 All migration paths now converge to single head")

def downgrade() -> None:
    """
    Downgrade would split back into multiple heads
    """
    print("⚠️  Downgrade would split back into multiple heads")
    # No actual operations needed for merge migration