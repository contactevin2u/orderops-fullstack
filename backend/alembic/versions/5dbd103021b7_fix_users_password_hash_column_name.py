
#!/usr/bin/env python


"""fix_users_password_hash_column_name

Revision ID: 5dbd103021b7
Revises: 55e6f79c4dff
Create Date: 2025-09-11 22:00:15.320601

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5dbd103021b7'
down_revision = '55e6f79c4dff'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Fix users.password_hash column name to match SQLAlchemy model"""
    
    # Use raw SQL to avoid SQLAlchemy model dependencies
    connection = op.get_bind()
    
    # First check if the column rename is needed
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('hashed_password', 'password_hash')
    """)).fetchall()
    
    columns = [row[0] for row in result]
    
    if 'hashed_password' in columns and 'password_hash' not in columns:
        print("🔧 Renaming users.hashed_password to users.password_hash")
        
        try:
            # Use raw SQL for the rename to avoid Alembic issues
            connection.execute(sa.text("""
                ALTER TABLE users 
                RENAME COLUMN hashed_password TO password_hash
            """))
            
            print("✅ Successfully renamed users.hashed_password to users.password_hash")
            print("✅ Frontend /register endpoint should now work!")
            
        except Exception as e:
            print(f"❌ Failed to rename column: {e}")
            print("⚠️  This will cause authentication issues")
            raise
            
    elif 'password_hash' in columns:
        print("✅ users.password_hash already exists - no action needed")
        
    else:
        print("❌ Neither hashed_password nor password_hash found in users table")
        print("⚠️  This indicates a serious database schema issue")

def downgrade() -> None:
    """Reverse the column rename"""
    connection = op.get_bind()
    
    try:
        connection.execute(sa.text("""
            ALTER TABLE users 
            RENAME COLUMN password_hash TO hashed_password
        """))
        print("✅ Reversed: users.password_hash -> users.hashed_password")
    except Exception as e:
        print(f"⚠️ Could not reverse column rename: {e}")
