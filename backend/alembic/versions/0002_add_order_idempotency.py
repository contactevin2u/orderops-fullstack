"""add order idempotency key"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_order_idempotency"
down_revision = "0001_init_fullstack"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    op.create_index("ix_orders_idempotency_key", "orders", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_orders_idempotency_key", table_name="orders")
    op.drop_column("orders", "idempotency_key")
