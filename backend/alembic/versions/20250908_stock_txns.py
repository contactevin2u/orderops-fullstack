"""Ghost revision - placeholder for database consistency

Revision ID: 20250908_stock_txns
Revises: 20250907_lorry_models
Create Date: 2025-09-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250908_stock_txns'
down_revision = '20250907_lorry_models'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - database thinks this exists
    # Do nothing, just let it pass
    print("👻 Ghost revision - doing nothing")
    pass


def downgrade():
    # Ghost revision - do nothing
    pass