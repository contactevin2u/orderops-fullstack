"""add closure_reason to driver_shifts and backfill closed rows

Revision ID: 20250913b_add_closure_reason_and_backfill
Revises: add_closure_reason_001
Create Date: 2025-09-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250913b_add_closure_reason_and_backfill"
down_revision = "add_closure_reason_001"
branch_labels = None
depends_on = None

def upgrade():
    # 1) Add the column (safe even if run once)
    op.add_column("driver_shifts", sa.Column("closure_reason", sa.Text(), nullable=True))

    # 2) Backfill closure_reason for already-closed shifts (they existed before policy)
    # We don't guess a reason; just mark them LEGACY if missing.
    op.execute("""
        UPDATE driver_shifts
           SET closure_reason = 'LEGACY'
         WHERE clock_out_at IS NOT NULL
           AND closure_reason IS NULL;
    """)

def downgrade():
    op.drop_column("driver_shifts", "closure_reason")