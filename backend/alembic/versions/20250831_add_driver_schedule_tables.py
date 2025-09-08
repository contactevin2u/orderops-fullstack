"""Ghost revision - 20250831_add_driver_schedule_tables

Revision ID: 20250831_add_driver_schedule_tables
Revises: 20250831_add_driver_clock_system
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250831_add_driver_schedule_tables'
down_revision = '20250831_add_driver_clock_system'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 20250831_add_driver_schedule_tables - doing nothing")
    pass


def downgrade():
    pass
