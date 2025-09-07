
#!/usr/bin/env python


"""Fix PostgreSQL enum types for UID inventory

Revision ID: 3c8b1c03e2ca
Revises: 0015_merge_heads
Create Date: 2025-09-07 09:26:59.499561

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3c8b1c03e2ca'
down_revision = '0015_merge_heads'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Simple, safe approach: just ensure enum types exist with correct values
    conn = op.get_bind()
    
    # Create enum types if they don't exist
    conn.execute(sa.text("""
        DO $$ 
        BEGIN
            -- Create itemstatus enum if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itemstatus') THEN
                CREATE TYPE itemstatus AS ENUM ('WAREHOUSE', 'WITH_DRIVER', 'DELIVERED', 'RETURNED', 'IN_REPAIR', 'DISCONTINUED');
            END IF;
            
            -- Create itemtype enum if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itemtype') THEN
                CREATE TYPE itemtype AS ENUM ('NEW', 'RENTAL');
            END IF;
        END
        $$;
    """))

def downgrade() -> None:
    # Drop enum types
    conn = op.get_bind()
    conn.execute(sa.text("DROP TYPE IF EXISTS itemstatus"))
    conn.execute(sa.text("DROP TYPE IF EXISTS itemtype"))
