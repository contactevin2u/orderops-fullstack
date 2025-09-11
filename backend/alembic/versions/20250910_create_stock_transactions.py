"""Create lorry_stock_transactions table

Revision ID: 20250910_stock_transactions  
Revises: 20250908_stock_txns
Create Date: 2025-09-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250910_stock_transactions'
down_revision = '20250908_stock_txns'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - doing nothing (base tables don't exist yet)
    print("👻 Ghost lorry_stock_transactions migration - doing nothing")


def downgrade():
    # Ghost revision - doing nothing
    print("👻 Ghost lorry_stock_transactions downgrade - doing nothing")