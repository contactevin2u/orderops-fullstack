"""Ghost revision - 0009_add_driver_routes

Revision ID: 0009_add_driver_routes
Revises: 0008_add_user_and_audit
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009_add_driver_routes'
down_revision = '0008_add_user_and_audit'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0009_add_driver_routes - doing nothing")
    pass


def downgrade():
    pass
