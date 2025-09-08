"""Ghost revision - 0008_add_user_and_audit

Revision ID: 0008_add_user_and_audit
Revises: 0007_add_trip_commission_tables
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008_add_user_and_audit'
down_revision = '0007_add_trip_commission_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0008_add_user_and_audit - doing nothing")
    pass


def downgrade():
    pass
