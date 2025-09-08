"""Ghost revision - 0012_add_multiple_pod_photos

Revision ID: 0012_add_multiple_pod_photos
Revises: 0011_add_upfront_billed_to_plans
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0012_add_multiple_pod_photos'
down_revision = '0011_add_upfront_billed_to_plans'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost 0012_add_multiple_pod_photos - doing nothing")
    pass


def downgrade():
    pass
