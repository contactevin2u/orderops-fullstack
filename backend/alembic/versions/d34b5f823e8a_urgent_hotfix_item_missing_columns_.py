
#!/usr/bin/env python


"""urgent_hotfix_item_missing_columns_comprehensive

Revision ID: d34b5f823e8a
Revises: 20f95ed91270
Create Date: 2025-09-12 19:08:05.508046

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd34b5f823e8a'
down_revision = '20f95ed91270'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Comprehensive hotfix for item table missing all other columns
    connection = op.get_bind()
    
    try:
        print("🚨 URGENT: Fixing item table missing columns (comprehensive)...")
        
        # Create ItemStatus enum if it doesn't exist
        connection.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE itemstatus AS ENUM (
                    'WAREHOUSE', 'WITH_DRIVER', 'DELIVERED', 'RETURNED', 'IN_REPAIR', 'DISCONTINUED'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$
        """))
        print("✅ Created/verified ItemStatus enum")
        
        # List of columns to check and add
        columns_to_add = [
            ('copy_number', 'INTEGER'),
            ('oem_serial', 'VARCHAR'),
            ('status', "itemstatus NOT NULL DEFAULT 'WAREHOUSE'"),
            ('current_driver_id', 'INTEGER REFERENCES drivers(id)'),
            ('created_at', 'TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP')
        ]
        
        for col_name, col_def in columns_to_add:
            # Check if column exists
            result = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'item' AND column_name = '{col_name}'
            """))
            
            if result.fetchone() is None:
                connection.execute(sa.text(f"""
                    ALTER TABLE item ADD COLUMN {col_name} {col_def}
                """))
                print(f"✅ Added {col_name} column to item table")
        
        connection.commit()
        print("✅ Urgent item table comprehensive hotfix completed successfully")
        
    except Exception as e:
        print(f"⚠️ Urgent hotfix error: {e}")
        connection.rollback()
        raise

def downgrade() -> None:
    # Remove the added columns
    connection = op.get_bind()
    
    try:
        columns_to_remove = [
            'created_at', 'current_driver_id', 'status', 'oem_serial', 'copy_number'
        ]
        
        for col in columns_to_remove:
            connection.execute(sa.text(f"ALTER TABLE item DROP COLUMN IF EXISTS {col}"))
        
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
