
#!/usr/bin/env python


"""fix_audit_logs_table_schema

Revision ID: ccbccb165e0a
Revises: 16b7d5977eb6
Create Date: 2025-09-12 17:56:37.939686

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ccbccb165e0a'
down_revision = '16b7d5977eb6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # URGENT HOTFIX: Fix audit_logs table schema to prevent SKU creation 500 errors
    # This addresses the log_action() function failures in SKU operations
    
    connection = op.get_bind()
    
    # Check if audit_logs table exists
    try:
        result = connection.execute(sa.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'audit_logs'
        """))
        
        if result.fetchone() is None:
            # Table doesn't exist, create it with correct schema
            connection.execute(sa.text("""
                CREATE TABLE audit_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action VARCHAR(100) NOT NULL,
                    details JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            print("✅ HOTFIX: Created audit_logs table with correct schema")
        else:
            # Table exists, check and add missing columns
            required_columns = [
                ('id', 'SERIAL PRIMARY KEY'),
                ('user_id', 'INTEGER REFERENCES users(id)'),
                ('action', 'VARCHAR(100) NOT NULL'),
                ('details', 'JSON'),
                ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
            ]
            
            for col_name, col_def in required_columns:
                result = connection.execute(sa.text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'audit_logs' 
                    AND column_name = '{col_name}'
                """))
                
                if result.fetchone() is None:
                    if col_name == 'id':
                        # Special handling for primary key
                        connection.execute(sa.text("""
                            ALTER TABLE audit_logs 
                            ADD COLUMN id SERIAL PRIMARY KEY
                        """))
                    elif col_name == 'user_id':
                        connection.execute(sa.text(f"""
                            ALTER TABLE audit_logs 
                            ADD COLUMN {col_name} {col_def}
                        """))
                    else:
                        connection.execute(sa.text(f"""
                            ALTER TABLE audit_logs 
                            ADD COLUMN {col_name} {col_def}
                        """))
                    print(f"✅ HOTFIX: Added {col_name} column to audit_logs")
                    
        connection.commit()
        print("✅ HOTFIX: audit_logs table schema is now correct")
        
    except Exception as e:
        print(f"⚠️  HOTFIX Error: {e}")
        connection.rollback()

def downgrade() -> None:
    # Remove audit_logs table if we created it, or just the added columns
    connection = op.get_bind()
    
    try:
        # Check if table exists
        result = connection.execute(sa.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'audit_logs'
        """))
        
        if result.fetchone() is not None:
            # Drop the entire table since we may have created it
            connection.execute(sa.text("DROP TABLE IF EXISTS audit_logs CASCADE"))
            print("✅ Removed audit_logs table")
            
        connection.commit()
        
    except Exception as e:
        print(f"⚠️  Downgrade Error: {e}")
        connection.rollback()
