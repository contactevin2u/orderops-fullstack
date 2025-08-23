"""add parent_id to orders and idempotent requests table"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_parent_and_idempotent"
down_revision = "0003_add_returned_at_to_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("parent_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_orders_parent_id", "orders", ["parent_id"])
    op.create_foreign_key(
        "orders_parent_id_fkey", "orders", "orders", ["parent_id"], ["id"], ondelete="SET NULL"
    )
    op.create_table(
        "idempotent_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.BigInteger(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_idempotent_requests_key", "idempotent_requests", ["key"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_idempotent_requests_key", table_name="idempotent_requests")
    op.drop_table("idempotent_requests")
    op.drop_constraint("orders_parent_id_fkey", "orders", type_="foreignkey")
    op.drop_index("ix_orders_parent_id", table_name="orders")
    op.drop_column("orders", "parent_id")
