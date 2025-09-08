"""Ghost revision - enum types placeholder

Revision ID: 3c8b1c03e2ca
Revises: 0015_merge_heads
Create Date: 2025-09-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c8b1c03e2ca'
down_revision = '0015_merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - database thinks this exists
    print("👻 Ghost enum types revision - doing nothing")
    pass


def downgrade():
    # Ghost revision - do nothing  
    pass