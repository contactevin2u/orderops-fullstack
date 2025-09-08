"""Ghost revision - 0004_add_parent_and_idempotent

Revision ID: 0004_add_parent_and_idempotent
Revises: 0003_add_returned_at_to_orders
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_add_parent_and_idempotent'
down_revision = '0003_add_returned_at_to_orders'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0004_add_parent_and_idempotent - doing nothing")
    pass


def downgrade():
    pass
