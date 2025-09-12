
#!/usr/bin/env python


"""check_uid_tables

Revision ID: 1cf733189626
Revises: 3fae7045e025
Create Date: 2025-09-12 09:01:12.351312

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1cf733189626'
down_revision = '3fae7045e025'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Create item table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'item'"))
    if not result.fetchone():
        op.create_table(
            'item',
            sa.Column('uid', sa.String(), primary_key=True),
            sa.Column('sku_id', sa.Integer(), sa.ForeignKey('sku.id'), nullable=False),
            sa.Column('item_type', sa.Enum('NEW', 'RENTAL', name='itemtype'), nullable=False, server_default='RENTAL'),
            sa.Column('copy_number', sa.Integer(), nullable=True),
            sa.Column('oem_serial', sa.String(), nullable=True),
            sa.Column('status', sa.Enum('WAREHOUSE', 'WITH_DRIVER', 'DELIVERED', 'RETURNED', 'IN_REPAIR', 'DISCONTINUED', name='itemstatus'), nullable=False, server_default='WAREHOUSE'),
            sa.Column('current_driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )
        op.create_index('ix_item_sku_id', 'item', ['sku_id'])
        op.create_index('ix_item_status', 'item', ['status'])
        op.create_index('ix_item_current_driver_id', 'item', ['current_driver_id'])
    
    # 2. Create order_item_uid table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'order_item_uid'"))
    if not result.fetchone():
        op.create_table(
            'order_item_uid',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
            sa.Column('uid', sa.String(), sa.ForeignKey('item.uid'), nullable=False),
            sa.Column('scanned_by', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('scanned_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('action', sa.Enum('LOAD_OUT', 'DELIVER', 'RETURN', 'REPAIR', 'SWAP', 'LOAD_IN', 'ISSUE', name='uidaction'), nullable=False),
            sa.Column('sku_id', sa.Integer(), sa.ForeignKey('sku.id'), nullable=True),
            sa.Column('sku_name', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
        )
        op.create_index('ix_order_item_uid_order_id', 'order_item_uid', ['order_id'])
        op.create_index('ix_order_item_uid_uid', 'order_item_uid', ['uid'])
        op.create_index('ix_order_item_uid_scanned_by', 'order_item_uid', ['scanned_by'])
        op.create_index('ix_order_item_uid_scanned_at', 'order_item_uid', ['scanned_at'])
    
    # 3. Create uid_ledger table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'uid_ledger'"))
    if not result.fetchone():
        op.create_table(
            'uid_ledger',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uid', sa.String(), sa.ForeignKey('item.uid'), nullable=False),
            sa.Column('action', sa.Enum('LOAD_OUT', 'DELIVER', 'RETURN', 'REPAIR', 'SWAP', 'LOAD_IN', 'ISSUE', name='uidaction'), nullable=False),
            sa.Column('scanned_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('scanned_by_admin', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('scanned_by_driver', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=True),
            sa.Column('scanner_name', sa.String(), nullable=True),
            sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
            sa.Column('sku_id', sa.Integer(), sa.ForeignKey('sku.id'), nullable=True),
            sa.Column('source', sa.Enum('ADMIN_MANUAL', 'DRIVER_SYNC', 'ORDER_OPERATION', 'INVENTORY_AUDIT', 'MAINTENANCE', 'SYSTEM_IMPORT', name='ledgerentrysource'), nullable=False, server_default='ADMIN_MANUAL'),
            sa.Column('lorry_id', sa.String(), nullable=True),
            sa.Column('location_notes', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('customer_name', sa.String(), nullable=True),
            sa.Column('order_reference', sa.String(), nullable=True),
            sa.Column('driver_scan_id', sa.String(), nullable=True, unique=True),
            sa.Column('sync_status', sa.String(), nullable=False, server_default='RECORDED'),
            sa.Column('recorded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('deleted_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('deletion_reason', sa.Text(), nullable=True),
        )
        op.create_index('ix_uid_ledger_uid', 'uid_ledger', ['uid'])
        op.create_index('ix_uid_ledger_scanned_at', 'uid_ledger', ['scanned_at'])
        op.create_index('ix_uid_ledger_order_id', 'uid_ledger', ['order_id'])
        op.create_index('ix_uid_ledger_recorded_by', 'uid_ledger', ['recorded_by'])
        op.create_index('ix_uid_ledger_driver_scan_id', 'uid_ledger', ['driver_scan_id'])

def downgrade() -> None:
    connection = op.get_bind()
    
    # Drop tables in reverse order (child first, then parent)
    tables_to_drop = [
        ('uid_ledger', ['ix_uid_ledger_driver_scan_id', 'ix_uid_ledger_recorded_by', 'ix_uid_ledger_order_id', 'ix_uid_ledger_scanned_at', 'ix_uid_ledger_uid']),
        ('order_item_uid', ['ix_order_item_uid_scanned_at', 'ix_order_item_uid_scanned_by', 'ix_order_item_uid_uid', 'ix_order_item_uid_order_id']),
        ('item', ['ix_item_current_driver_id', 'ix_item_status', 'ix_item_sku_id']),
    ]
    
    for table_name, indexes in tables_to_drop:
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"))
        if result.fetchone():
            # Drop indexes first
            for index_name in indexes:
                try:
                    op.drop_index(index_name, table_name)
                except:
                    pass  # Index might not exist
            # Drop table
            op.drop_table(table_name)
    
    # Drop custom enum types if they exist
    try:
        op.execute("DROP TYPE IF EXISTS ledgerentrysource")
        op.execute("DROP TYPE IF EXISTS uidaction") 
        op.execute("DROP TYPE IF EXISTS itemstatus")
        op.execute("DROP TYPE IF EXISTS itemtype")
    except:
        pass  # Types might not exist
