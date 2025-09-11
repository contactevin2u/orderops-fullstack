#!/usr/bin/env python

"""Add UID ledger for medical device traceability

Revision ID: 20250911_add_uid_ledger
Revises: 8d6e613b90ed
Create Date: 2025-09-11 10:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '20250911_add_uid_ledger'
down_revision = '8d6e613b90ed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists to prevent errors
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if not inspector.has_table('uid_ledger'):
        # Check if uidaction enum already exists in PostgreSQL
        result = connection.execute(text("SELECT 1 FROM pg_type WHERE typname = 'uidaction'"))
        uidaction_exists = result.fetchone() is not None
        
        if not uidaction_exists:
            # Create the enum type
            op.execute("CREATE TYPE uidaction AS ENUM ('LOAD_OUT', 'DELIVER', 'RETURN', 'REPAIR', 'SWAP', 'LOAD_IN', 'ISSUE')")
        
        # Check if ledgerentrysource enum exists
        result = connection.execute(text("SELECT 1 FROM pg_type WHERE typname = 'ledgerentrysource'"))
        ledgerentrysource_exists = result.fetchone() is not None
        
        if not ledgerentrysource_exists:
            # Create the enum type
            op.execute("CREATE TYPE ledgerentrysource AS ENUM ('ADMIN_MANUAL', 'DRIVER_SYNC', 'ORDER_OPERATION', 'INVENTORY_AUDIT', 'MAINTENANCE', 'SYSTEM_IMPORT')")
        
        # Create UID ledger table for comprehensive medical device traceability
        # Use existing or newly created enum types
        uidaction_enum = sa.Enum('LOAD_OUT', 'DELIVER', 'RETURN', 'REPAIR', 'SWAP', 'LOAD_IN', 'ISSUE', name='uidaction', create_type=False)
        ledgerentrysource_enum = sa.Enum('ADMIN_MANUAL', 'DRIVER_SYNC', 'ORDER_OPERATION', 'INVENTORY_AUDIT', 'MAINTENANCE', 'SYSTEM_IMPORT', name='ledgerentrysource', create_type=False)
        
        op.create_table('uid_ledger',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('uid', sa.String(), nullable=False),
            sa.Column('action', uidaction_enum, nullable=False),
            sa.Column('scanned_at', sa.DateTime(), nullable=False),
            sa.Column('scanned_by_admin', sa.Integer(), nullable=True),
            sa.Column('scanned_by_driver', sa.Integer(), nullable=True),
            sa.Column('scanner_name', sa.String(), nullable=True),
            sa.Column('order_id', sa.Integer(), nullable=True),
            sa.Column('sku_id', sa.Integer(), nullable=True),
            sa.Column('source', ledgerentrysource_enum, nullable=False),
            sa.Column('lorry_id', sa.String(), nullable=True),
            sa.Column('location_notes', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('customer_name', sa.String(), nullable=True),
            sa.Column('order_reference', sa.String(), nullable=True),
            sa.Column('driver_scan_id', sa.String(), nullable=True),
            sa.Column('sync_status', sa.String(), nullable=False),
            sa.Column('recorded_by', sa.Integer(), nullable=False),
            sa.Column('recorded_at', sa.DateTime(), nullable=False),
            sa.Column('is_deleted', sa.Boolean(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('deleted_by', sa.Integer(), nullable=True),
            sa.Column('deletion_reason', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
            sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['scanned_by_admin'], ['users.id'], ),
            sa.ForeignKeyConstraint(['scanned_by_driver'], ['drivers.id'], ),
            sa.ForeignKeyConstraint(['sku_id'], ['sku.id'], ),
            sa.ForeignKeyConstraint(['uid'], ['item.uid'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('driver_scan_id')
        )
        
        # Create indexes for better query performance
        op.create_index('idx_uid_ledger_uid', 'uid_ledger', ['uid'])
        op.create_index('idx_uid_ledger_scanned_at', 'uid_ledger', ['scanned_at'])
        op.create_index('idx_uid_ledger_action', 'uid_ledger', ['action'])
        op.create_index('idx_uid_ledger_order_id', 'uid_ledger', ['order_id'])
        op.create_index('idx_uid_ledger_source', 'uid_ledger', ['source'])
        op.create_index('idx_uid_ledger_sync_status', 'uid_ledger', ['sync_status'])
        op.create_index('idx_uid_ledger_not_deleted', 'uid_ledger', ['is_deleted'])


def downgrade() -> None:
    # Check if table exists before trying to drop
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('uid_ledger'):
        # Drop indexes first (ignore errors if they don't exist)
        try:
            op.drop_index('idx_uid_ledger_not_deleted', table_name='uid_ledger')
        except Exception:
            pass
        try:
            op.drop_index('idx_uid_ledger_sync_status', table_name='uid_ledger')
        except Exception:
            pass
        try:
            op.drop_index('idx_uid_ledger_source', table_name='uid_ledger')
        except Exception:
            pass
        try:
            op.drop_index('idx_uid_ledger_order_id', table_name='uid_ledger')
        except Exception:
            pass
        try:
            op.drop_index('idx_uid_ledger_action', table_name='uid_ledger')
        except Exception:
            pass
        try:
            op.drop_index('idx_uid_ledger_scanned_at', table_name='uid_ledger')
        except Exception:
            pass
        try:
            op.drop_index('idx_uid_ledger_uid', table_name='uid_ledger')
        except Exception:
            pass
        
        # Drop table
        op.drop_table('uid_ledger')
        
        # Only drop enums if no other tables are using them
        # Check if any tables still use uidaction
        result = connection.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE udt_name = 'uidaction' AND table_name != 'uid_ledger'
        """))
        uidaction_usage = result.fetchone()[0]
        
        if uidaction_usage == 0:
            op.execute("DROP TYPE IF EXISTS uidaction")
        
        # ledgerentrysource should be safe to drop as it's only used by uid_ledger
        op.execute("DROP TYPE IF EXISTS ledgerentrysource")