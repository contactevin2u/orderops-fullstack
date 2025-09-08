"""Ghost revision - 0005_add_payment_export_fields

Revision ID: 0005_add_payment_export_fields
Revises: 0004_add_parent_and_idempotent
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_add_payment_export_fields'
down_revision = '0004_add_parent_and_idempotent'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0005_add_payment_export_fields - doing nothing")
    pass


def downgrade():
    pass
