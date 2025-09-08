"""Ghost revision - f36d7abf49c7

Revision ID: f36d7abf49c7
Revises: 0012_add_multiple_pod_photos
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f36d7abf49c7'
down_revision = '0012_add_multiple_pod_photos'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("👻 Ghost f36d7abf49c7 - doing nothing")
    pass


def downgrade():
    pass
