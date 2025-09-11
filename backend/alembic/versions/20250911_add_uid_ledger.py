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
    # Ghost revision - doing nothing (base tables don't exist yet)
    print("👻 Ghost UID ledger migration - doing nothing")
    return

def upgrade_original() -> None:
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
        
        # Create UID ledger table using raw SQL to avoid enum auto-creation issues
        op.execute("""
            CREATE TABLE uid_ledger (
                id SERIAL PRIMARY KEY,
                uid VARCHAR NOT NULL,
                action uidaction NOT NULL,
                scanned_at TIMESTAMP NOT NULL,
                scanned_by_admin INTEGER,
                scanned_by_driver INTEGER,
                scanner_name VARCHAR,
                order_id INTEGER,
                sku_id INTEGER,
                source ledgerentrysource NOT NULL,
                lorry_id VARCHAR,
                location_notes VARCHAR,
                notes TEXT,
                customer_name VARCHAR,
                order_reference VARCHAR,
                driver_scan_id VARCHAR UNIQUE,
                sync_status VARCHAR NOT NULL,
                recorded_by INTEGER NOT NULL,
                recorded_at TIMESTAMP NOT NULL,
                is_deleted BOOLEAN NOT NULL,
                deleted_at TIMESTAMP,
                deleted_by INTEGER,
                deletion_reason TEXT,
                FOREIGN KEY (deleted_by) REFERENCES users(id),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (recorded_by) REFERENCES users(id),
                FOREIGN KEY (scanned_by_admin) REFERENCES users(id),
                FOREIGN KEY (scanned_by_driver) REFERENCES drivers(id),
                FOREIGN KEY (sku_id) REFERENCES sku(id),
                FOREIGN KEY (uid) REFERENCES item(uid)
            )
        """)
        
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
        # Drop table and indexes using raw SQL
        op.execute("DROP TABLE IF EXISTS uid_ledger CASCADE")
        
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