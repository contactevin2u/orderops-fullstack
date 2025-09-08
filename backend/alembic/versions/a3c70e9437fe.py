"""Ghost revision - branch merge placeholder

Revision ID: a3c70e9437fe
Revises: ('20250902_upsell_records', 'bg_jobs_001')
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3c70e9437fe'
down_revision = ('20250902_upsell_records', 'bg_jobs_001')
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - database thinks this exists
    print("👻 Ghost branch merge revision - doing nothing")
    pass


def downgrade():
    # Ghost revision - do nothing
    pass