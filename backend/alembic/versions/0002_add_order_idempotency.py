"""Ghost revision - 0002_add_order_idempotency

Revision ID: 0002_add_order_idempotency
Revises: 0001_init_fullstack
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_order_idempotency'
down_revision = '0001_init_fullstack'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("Ghost 0002_add_order_idempotency - doing nothing")
    pass


def downgrade():
    pass
