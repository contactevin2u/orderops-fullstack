
#!/usr/bin/env python


"""fix_idempotent_requests_table_schema

Revision ID: 62fb995d6d46
Revises: ff3a4b5c6d7e
Create Date: 2025-09-12 17:23:34.261737

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '62fb995d6d46'
down_revision = 'ff3a4b5c6d7e'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if idempotent_requests table exists and has the wrong schema
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('idempotent_requests'):
        columns = [col['name'] for col in inspector.get_columns('idempotent_requests')]
        print(f"Current idempotent_requests columns: {columns}")
        
        # If the table has the wrong schema (missing id column), recreate it
        if 'id' not in columns:
            print("🔧 Fixing idempotent_requests table schema...")
            
            # Drop the incorrectly created table
            op.drop_table('idempotent_requests')
            
            # Create the correct table structure
            op.create_table('idempotent_requests',
                sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
                sa.Column('key', sa.String(length=64), nullable=False),
                sa.Column('order_id', sa.Integer(), nullable=False),
                sa.Column('action', sa.String(length=20), nullable=False),
                sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
                sa.PrimaryKeyConstraint('id'),
                sa.UniqueConstraint('key')
            )
            
            # Create index
            op.create_index('ix_idempotent_requests_key', 'idempotent_requests', ['key'])
            
            print("✅ Fixed idempotent_requests table schema")
        else:
            print("✅ idempotent_requests table already has correct schema")
    else:
        print("⚠️ idempotent_requests table doesn't exist - this shouldn't happen")

def downgrade() -> None:
    # This migration is just fixing schema, so downgrade would recreate the broken version
    # For simplicity, we'll just keep the correct version
    print("⚠️ Downgrade not implemented - keeping correct schema")
