"""Create lorry_stock_transactions table

Revision ID: 20250910_create_stock_transactions  
Revises: 20250908_stock_txns
Create Date: 2025-09-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250910_create_stock_transactions'
down_revision = '20250908_stock_txns'
branch_labels = None
depends_on = None


def upgrade():
    # Create lorry_stock_transactions table
    op.create_table('lorry_stock_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(50), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('uid', sa.String(100), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_lorry_stock_transactions_lorry_id', 'lorry_stock_transactions', ['lorry_id'])
    op.create_index('ix_lorry_stock_transactions_uid', 'lorry_stock_transactions', ['uid'])
    op.create_index('ix_lorry_stock_transactions_sku_id', 'lorry_stock_transactions', ['sku_id'])
    op.create_index('ix_lorry_stock_transactions_order_id', 'lorry_stock_transactions', ['order_id'])
    op.create_index('ix_lorry_stock_transactions_driver_id', 'lorry_stock_transactions', ['driver_id'])
    op.create_index('ix_lorry_stock_transactions_transaction_date', 'lorry_stock_transactions', ['transaction_date'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_lorry_stock_transactions_transaction_date', table_name='lorry_stock_transactions')
    op.drop_index('ix_lorry_stock_transactions_driver_id', table_name='lorry_stock_transactions')
    op.drop_index('ix_lorry_stock_transactions_order_id', table_name='lorry_stock_transactions')
    op.drop_index('ix_lorry_stock_transactions_sku_id', table_name='lorry_stock_transactions')
    op.drop_index('ix_lorry_stock_transactions_uid', table_name='lorry_stock_transactions')
    op.drop_index('ix_lorry_stock_transactions_lorry_id', table_name='lorry_stock_transactions')
    
    # Drop table
    op.drop_table('lorry_stock_transactions')