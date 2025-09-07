
#!/usr/bin/env python


"""Create complete UID inventory system with proper enums

Revision ID: f65ddd477595
Revises: 0015_merge_heads
Create Date: 2025-09-07 09:01:41.217933

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f65ddd477595'
down_revision = '0015_merge_heads'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create PostgreSQL enum types first
    from sqlalchemy.dialects import postgresql
    
    itemstatus_enum = postgresql.ENUM(
        'WAREHOUSE', 'WITH_DRIVER', 'DELIVERED', 'RETURNED', 'IN_REPAIR', 'DISCONTINUED',
        name='itemstatus',
        create_type=False
    )
    itemstatus_enum.create(op.get_bind(), checkfirst=True)
    
    itemtype_enum = postgresql.ENUM(
        'NEW', 'RENTAL',
        name='itemtype', 
        create_type=False
    )
    itemtype_enum.create(op.get_bind(), checkfirst=True)
    
    # Create SKU table if it doesn't exist
    try:
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
    except Exception:
        # SKU table may already exist
        pass
    
    # Create item table for UID tracking
    try:
        op.create_table(
            'item',
            sa.Column('uid', sa.String, primary_key=True),
            sa.Column('sku_id', sa.Integer, nullable=False),
            sa.Column('item_type', itemtype_enum, nullable=False, default='RENTAL'),
            sa.Column('copy_number', sa.Integer, nullable=True),
            sa.Column('oem_serial', sa.String, nullable=True),
            sa.Column('status', itemstatus_enum, nullable=False, default='WAREHOUSE'),
            sa.Column('current_driver_id', sa.Integer, nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
            sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
            sa.ForeignKeyConstraint(['current_driver_id'], ['drivers.id']),
            sa.Index('ix_item_sku_id', 'sku_id'),
            sa.Index('ix_item_status', 'status')
        )
    except Exception:
        pass
    
    # Create order_item_uid table for tracking UID assignments
    try:
        op.create_table(
            'order_item_uid',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.Integer, nullable=False),
            sa.Column('uid', sa.String, nullable=False),
            sa.Column('scanned_by', sa.Integer, nullable=False),
            sa.Column('scanned_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
            sa.Column('action', sa.String, nullable=False),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
            sa.ForeignKeyConstraint(['uid'], ['item.uid']),
            sa.ForeignKeyConstraint(['scanned_by'], ['drivers.id']),
            sa.CheckConstraint("action IN ('LOAD_OUT', 'DELIVER', 'RETURN', 'REPAIR', 'SWAP', 'LOAD_IN', 'ISSUE')", name='ck_order_item_uid_action'),
            sa.UniqueConstraint('order_id', 'uid', 'action', name='uq_order_item_uid_order_uid_action'),
            sa.Index('ix_order_item_uid_order_id_action', 'order_id', 'action'),
            sa.Index('ix_order_item_uid_uid', 'uid')
        )
    except Exception:
        pass
    
    # Create lorry_stock table for daily driver stock snapshots
    try:
        op.create_table(
            'lorry_stock',
            sa.Column('driver_id', sa.Integer, nullable=False),
            sa.Column('as_of_date', sa.Date, nullable=False),
            sa.Column('sku_id', sa.Integer, nullable=False),
            sa.Column('qty_counted', sa.Integer, nullable=False),
            sa.Column('uploaded_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
            sa.Column('uploaded_by', sa.Integer, nullable=False),
            sa.PrimaryKeyConstraint('driver_id', 'as_of_date', 'sku_id'),
            sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
            sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
            sa.ForeignKeyConstraint(['uploaded_by'], ['drivers.id']),
            sa.Index('ix_lorry_stock_driver_date', 'driver_id', 'as_of_date')
        )
    except Exception:
        pass
    
    # Create sku_alias table for name matching
    try:
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
    except Exception:
        pass

def downgrade() -> None:
    # Drop tables
    try:
        op.drop_table('sku_alias')
    except Exception:
        pass
    try:
        op.drop_table('lorry_stock')
    except Exception:
        pass
    try:
        op.drop_table('order_item_uid')
    except Exception:
        pass
    try:
        op.drop_table('item')
    except Exception:
        pass
    
    # Drop enum types
    from sqlalchemy.dialects import postgresql
    try:
        itemstatus_enum = postgresql.ENUM(name='itemstatus')
        itemstatus_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
    
    try:
        itemtype_enum = postgresql.ENUM(name='itemtype')
        itemtype_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
