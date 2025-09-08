"""Ghost revision - 0003_add_returned_at_to_orders

Revision ID: 0003_add_returned_at_to_orders
Revises: 0002_add_order_idempotency
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_add_returned_at_to_orders'
down_revision = '0002_add_order_idempotency'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0003_add_returned_at_to_orders - doing nothing")
    pass


def downgrade():
    pass
