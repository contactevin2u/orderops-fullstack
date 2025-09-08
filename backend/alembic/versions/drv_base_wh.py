"""Ghost revision - driver base warehouse placeholder

Revision ID: drv_base_wh
Revises: a3c70e9437fe
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'drv_base_wh'
down_revision = 'a3c70e9437fe'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - database thinks this exists
    print("👻 Ghost driver base warehouse revision - doing nothing")
    pass


def downgrade():
    # Ghost revision - do nothing
    pass