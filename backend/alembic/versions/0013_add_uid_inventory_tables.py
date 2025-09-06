
#!/usr/bin/env python


"""Add UID inventory system tables

Revision ID: 5852c5f76a34
Revises: drv_base_wh
Create Date: 2025-09-05 20:31:20.242710

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0013_add_uid_inventory_tables'
down_revision = '20250902_upsell_records'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create SKU table first (referenced by other tables)
    op.create_table(
        'sku',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_serialized', sa.Boolean, nullable=False, default=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.UniqueConstraint('code', name='uq_sku_code'),
        sa.Index('ix_sku_code', 'code'),
        sa.Index('ix_sku_category', 'category'),
        sa.Index('ix_sku_is_serialized', 'is_serialized')
    )
    
    # Create item table for UID tracking
    op.create_table(
        'item',
        sa.Column('uid', sa.String, primary_key=True),
        sa.Column('sku_id', sa.Integer, nullable=False),
        sa.Column('oem_serial', sa.String, nullable=True),
        sa.Column('status', sa.String, nullable=False, default='ACTIVE'),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.Index('ix_item_sku_id', 'sku_id'),
        sa.Index('ix_item_status', 'status')
    )
    
    # Create order_item_uid table for tracking UID assignments
    op.create_table(
        'order_item_uid',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer, nullable=False),
        sa.Column('uid', sa.String, nullable=False),
        sa.Column('scanned_by', sa.Integer, nullable=False),
        sa.Column('scanned_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.Column('action', sa.String, nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['order.id']),
        sa.ForeignKeyConstraint(['uid'], ['item.uid']),
        sa.ForeignKeyConstraint(['scanned_by'], ['driver.id']),
        sa.CheckConstraint("action IN ('ISSUE', 'RETURN')", name='ck_order_item_uid_action'),
        sa.UniqueConstraint('order_id', 'uid', 'action', name='uq_order_item_uid_order_uid_action'),
        sa.Index('ix_order_item_uid_order_id_action', 'order_id', 'action'),
        sa.Index('ix_order_item_uid_uid', 'uid')
    )
    
    # Create lorry_stock table for daily driver stock snapshots
    op.create_table(
        'lorry_stock',
        sa.Column('driver_id', sa.Integer, nullable=False),
        sa.Column('as_of_date', sa.Date, nullable=False),
        sa.Column('sku_id', sa.Integer, nullable=False),
        sa.Column('qty_counted', sa.Integer, nullable=False),
        sa.Column('uploaded_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.Column('uploaded_by', sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint('driver_id', 'as_of_date', 'sku_id'),
        sa.ForeignKeyConstraint(['driver_id'], ['driver.id']),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['driver.id']),
        sa.Index('ix_lorry_stock_driver_date', 'driver_id', 'as_of_date')
    )
    
    # Create sku_alias table for name matching
    op.create_table(
        'sku_alias',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('sku_id', sa.Integer, nullable=False),
        sa.Column('alias_text', sa.String, nullable=False),
        sa.Column('weight', sa.Integer, nullable=False, default=1),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.UniqueConstraint('sku_id', 'alias_text', name='uq_sku_alias_sku_text'),
        sa.Index('ix_sku_alias_sku_id', 'sku_id'),
        sa.Index('ix_sku_alias_text', 'alias_text')
    )

def downgrade() -> None:
    op.drop_table('sku_alias')
    op.drop_table('lorry_stock')
    op.drop_table('order_item_uid')
    op.drop_table('item')
    op.drop_table('sku')
