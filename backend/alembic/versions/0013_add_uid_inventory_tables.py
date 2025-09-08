"""Ghost revision - add uid inventory tables placeholder

Revision ID: 0013_add_uid_inventory_tables
Revises: 20250902_upsell_records
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0013_add_uid_inventory_tables'
down_revision = '20250902_upsell_records'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - database thinks this exists
    print("👻 Ghost add uid inventory tables revision - doing nothing")
    pass


def downgrade():
    # Ghost revision - do nothing
    pass