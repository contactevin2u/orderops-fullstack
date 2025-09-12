
#!/usr/bin/env python


"""urgent_hotfix_item_missing_item_type_column

Revision ID: 20f95ed91270
Revises: d8de5a2d905f
Create Date: 2025-09-12 18:57:27.131380

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20f95ed91270'
down_revision = 'd8de5a2d905f'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Urgent hotfix for item table missing item_type column
    connection = op.get_bind()
    
    try:
        print("🚨 URGENT: Fixing item table missing item_type column...")
        
        # First, create the ItemType enum if it doesn't exist
        connection.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE itemtype AS ENUM ('NEW', 'RENTAL');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$
        """))
        print("✅ Created/verified ItemType enum")
        
        # Check if item_type column exists
        result = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'item' AND column_name = 'item_type'
        """))
        
        if result.fetchone() is None:
            connection.execute(sa.text("""
                ALTER TABLE item ADD COLUMN item_type itemtype NOT NULL DEFAULT 'RENTAL'
            """))
            print("✅ Added item_type column to item table")
        
        connection.commit()
        print("✅ Urgent item table hotfix completed successfully")
        
    except Exception as e:
        print(f"⚠️ Urgent hotfix error: {e}")
        connection.rollback()
        raise

def downgrade() -> None:
    # Remove the added column
    connection = op.get_bind()
    
    try:
        connection.execute(sa.text("ALTER TABLE item DROP COLUMN IF EXISTS item_type"))
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
