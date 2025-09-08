"""Ghost revision - merge heads placeholder

Revision ID: 0015_merge_heads
Revises: 0014_enhance_uid_system, drv_base_wh
Create Date: 2025-09-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0015_merge_heads'
down_revision = ('0014_enhance_uid_system', 'drv_base_wh')
branch_labels = None
depends_on = None


def upgrade():
    # Ghost merge revision
    print("👻 Ghost merge heads revision - doing nothing")
    pass


def downgrade():
    pass