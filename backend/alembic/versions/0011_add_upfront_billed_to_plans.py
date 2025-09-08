"""Ghost revision - 0011_add_upfront_billed_to_plans

Revision ID: 0011_add_upfront_billed_to_plans
Revises: 0010_update_driver_device_fields
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0011_add_upfront_billed_to_plans'
down_revision = '0010_update_driver_device_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0011_add_upfront_billed_to_plans - doing nothing")
    pass


def downgrade():
    pass
