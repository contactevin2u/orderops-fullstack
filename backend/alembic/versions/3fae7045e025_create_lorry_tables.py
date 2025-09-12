
#!/usr/bin/env python


"""create_lorry_tables

Revision ID: 3fae7045e025
Revises: 8636cff57ace
Create Date: 2025-09-12 08:57:07.212848

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3fae7045e025'
down_revision = '8636cff57ace'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Create lorries table
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'lorries'"))
    if not result.fetchone():
        op.create_table(
            'lorries',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('lorry_id', sa.String(50), nullable=False, unique=True),
            sa.Column('plate_number', sa.String(20), nullable=True),
            sa.Column('model', sa.String(100), nullable=True),
            sa.Column('capacity', sa.String(50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('is_available', sa.Boolean(), nullable=False, default=True),
            sa.Column('base_warehouse', sa.String(20), nullable=False, default='BATU_CAVES'),
            sa.Column('current_location', sa.String(100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('last_maintenance_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_lorries_lorry_id', 'lorries', ['lorry_id'])
        op.create_index('ix_lorries_plate_number', 'lorries', ['plate_number'])

    # 2. Create lorry_stock table
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'lorry_stock'"))
    if not result.fetchone():
        op.create_table(
            'lorry_stock',
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), primary_key=True),
            sa.Column('as_of_date', sa.Date(), primary_key=True),
            sa.Column('sku_id', sa.Integer(), sa.ForeignKey('sku.id'), primary_key=True),
            sa.Column('qty_counted', sa.Integer(), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
        )

    # 3. Create lorry_assignments table
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'lorry_assignments'"))
    if not result.fetchone():
        op.create_table(
            'lorry_assignments',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('lorry_id', sa.String(50), nullable=False),
            sa.Column('assignment_date', sa.Date(), nullable=False),
            sa.Column('shift_id', sa.BigInteger(), nullable=True),  # Will FK to driver_shifts when that exists
            sa.Column('stock_verified', sa.Boolean(), nullable=False, default=False),
            sa.Column('stock_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, default='ASSIGNED'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('assigned_by', sa.BigInteger(), nullable=False),  # Will FK to users when that exists  
            sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_lorry_assignments_driver_id', 'lorry_assignments', ['driver_id'])
        op.create_index('ix_lorry_assignments_lorry_id', 'lorry_assignments', ['lorry_id'])
        op.create_index('ix_lorry_assignments_assignment_date', 'lorry_assignments', ['assignment_date'])

def downgrade() -> None:
    connection = op.get_bind()
    
    # Drop tables in reverse order (child first, then parent)
    tables_to_drop = [
        ('lorry_assignments', ['ix_lorry_assignments_assignment_date', 'ix_lorry_assignments_lorry_id', 'ix_lorry_assignments_driver_id']),
        ('lorry_stock', []),
        ('lorries', ['ix_lorries_plate_number', 'ix_lorries_lorry_id']),
    ]
    
    for table_name, indexes in tables_to_drop:
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"))
        if result.fetchone():
            # Drop indexes first
            for index_name in indexes:
                op.drop_index(index_name, table_name)
            # Drop table
            op.drop_table(table_name)
