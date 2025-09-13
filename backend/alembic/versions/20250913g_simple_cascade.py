"""simple CASCADE database reset - one command approach

Revision ID: 20250913g_simple_cascade  
Revises: 20250913f_cascade_cleanup
Create Date: 2025-09-13 19:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250913g_simple_cascade'
down_revision = '20250913f_cascade_cleanup'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Ultra-simple approach: Use CASCADE to drop everything except users table
    Let PostgreSQL figure out the dependencies automatically
    """
    print("🧹 SIMPLE CASCADE: Let PostgreSQL handle all dependencies...")
    
    # Get all table names except users and alembic_version
    conn = op.get_bind()
    
    # Get all tables except system tables
    result = conn.exec_driver_sql("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename NOT IN ('users', 'alembic_version')
        ORDER BY tablename
    """)
    
    tables = [row[0] for row in result.fetchall()]
    
    print(f"📋 Found {len(tables)} tables to remove...")
    for table in tables:
        print(f"  - {table}")
    
    # Drop each table with CASCADE - let PostgreSQL handle dependencies
    for table in tables:
        try:
            print(f"🗑️  Dropping {table} with CASCADE...")
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"✅ Dropped {table}")
        except Exception as e:
            print(f"⚠️  Could not drop {table}: {e}")
            # Continue with next table
            continue
    
    # Verify users table still exists
    try:
        user_count = conn.exec_driver_sql("SELECT COUNT(*) FROM users").scalar()
        print(f"👤 Users table preserved with {user_count} users")
    except Exception as e:
        print(f"⚠️  Could not verify users table: {e}")
    
    print("🎉 Simple CASCADE cleanup completed!")
    print("📋 Database is now clean and ready for fresh schema")

def downgrade() -> None:
    """Cannot restore CASCADE-deleted data"""
    print("❌ Cannot restore CASCADE-deleted data")
    print("💡 Use database backup to restore if needed")