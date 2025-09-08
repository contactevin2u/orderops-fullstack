"""Ghost revision - lorry models placeholder

Revision ID: 20250907_lorry_models  
Revises: 3c8b1c03e2ca
Create Date: 2025-09-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250907_lorry_models'
down_revision = '3c8b1c03e2ca'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - database thinks this exists
    print("👻 Ghost lorry models revision - doing nothing") 
    pass


def downgrade():
    # Ghost revision - do nothing
    pass