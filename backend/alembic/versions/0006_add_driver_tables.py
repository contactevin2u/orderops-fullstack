"""Ghost revision - 0006_add_driver_tables

Revision ID: 0006_add_driver_tables
Revises: 0005_add_payment_export_fields
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_add_driver_tables'
down_revision = '0005_add_payment_export_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0006_add_driver_tables - doing nothing")
    pass


def downgrade():
    pass
