"""Ghost revision - 0010_update_driver_device_fields

Revision ID: 0010_update_driver_device_fields
Revises: 0009_add_driver_routes
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0010_update_driver_device_fields'
down_revision = '0009_add_driver_routes'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0010_update_driver_device_fields - doing nothing")
    pass


def downgrade():
    pass
