"""Add complete lorry management system

Revision ID: 20250908_complete_lorry_system
Revises: 20250907_lorry_models
Create Date: 2025-09-08 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250908_complete_lorry_system'
down_revision = '20250907_lorry_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create lorries table
    op.create_table('lorries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('plate_number', sa.String(length=20), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('capacity', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('base_warehouse', sa.String(length=20), nullable=False),
        sa.Column('current_location', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_maintenance_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lorries_lorry_id'), 'lorries', ['lorry_id'], unique=True)
    op.create_index(op.f('ix_lorries_plate_number'), 'lorries', ['plate_number'], unique=False)

    # Create lorry_stock_transactions table
    op.create_table('lorry_stock_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('uid', sa.String(length=100), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lorry_stock_transactions_lorry_id'), 'lorry_stock_transactions', ['lorry_id'], unique=False)
    op.create_index(op.f('ix_lorry_stock_transactions_uid'), 'lorry_stock_transactions', ['uid'], unique=False)
    op.create_index(op.f('ix_lorry_stock_transactions_transaction_date'), 'lorry_stock_transactions', ['transaction_date'], unique=False)

    # Add priority_lorry_id to drivers table
    op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_drivers_priority_lorry_id'), 'drivers', ['priority_lorry_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_drivers_priority_lorry_id'), table_name='drivers')
    op.drop_column('drivers', 'priority_lorry_id')
    
    op.drop_index(op.f('ix_lorry_stock_transactions_transaction_date'), table_name='lorry_stock_transactions')
    op.drop_index(op.f('ix_lorry_stock_transactions_uid'), table_name='lorry_stock_transactions')
    op.drop_index(op.f('ix_lorry_stock_transactions_lorry_id'), table_name='lorry_stock_transactions')
    op.drop_table('lorry_stock_transactions')
    
    op.drop_index(op.f('ix_lorries_plate_number'), table_name='lorries')
    op.drop_index(op.f('ix_lorries_lorry_id'), table_name='lorries')
    op.drop_table('lorries')