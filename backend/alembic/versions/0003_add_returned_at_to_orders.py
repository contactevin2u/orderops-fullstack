"""add returned_at column to orders"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_returned_at_to_orders"
down_revision = "0002_add_order_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "returned_at")
