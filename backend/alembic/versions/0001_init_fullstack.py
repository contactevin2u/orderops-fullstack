"""Ghost revision - 0001_init_fullstack

Revision ID: 0001_init_fullstack
Revises: 
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_init_fullstack'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - does nothing
    print("Ghost 0001_init_fullstack - doing nothing")
    pass


def downgrade():
    pass