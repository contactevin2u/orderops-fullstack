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
    # Check if table exists before creating it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if not inspector.has_table('lorry_stock_transactions'):
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
    
    # Create indexes if they don't exist
    existing_indexes = inspector.get_indexes('lorry_stock_transactions') if inspector.has_table('lorry_stock_transactions') else []
    existing_index_names = {idx['name'] for idx in existing_indexes}
    
    indexes_to_create = [
        ('ix_lorry_stock_transactions_lorry_id', ['lorry_id']),
        ('ix_lorry_stock_transactions_uid', ['uid']),
        ('ix_lorry_stock_transactions_sku_id', ['sku_id']),
        ('ix_lorry_stock_transactions_order_id', ['order_id']),
        ('ix_lorry_stock_transactions_driver_id', ['driver_id']),
        ('ix_lorry_stock_transactions_transaction_date', ['transaction_date'])
    ]
    
    for index_name, columns in indexes_to_create:
        if index_name not in existing_index_names:
            op.create_index(index_name, 'lorry_stock_transactions', columns)


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