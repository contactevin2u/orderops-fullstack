"""Fresh start: Add missing priority_lorry_id column

Revision ID: 001_fresh_start
Revises: 
Create Date: 2025-09-08 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = '001_fresh_start'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Fresh start migration - assumes all tables exist from previous deployments.
    Only adds the missing priority_lorry_id column that's breaking everything.
    """
    conn = op.get_bind()
    
    print("🔥 FRESH START MIGRATION")
    
    # Clear alembic_version table to start fresh
    try:
        conn.execute(text("DELETE FROM alembic_version"))
        print("✅ Cleared alembic version history")
    except:
        print("⚠️  Could not clear alembic_version (table may not exist)")
    
    # Check if drivers table exists
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'drivers' not in tables:
        print("❌ drivers table doesn't exist - cannot proceed")
        return
        
    # Check if priority_lorry_id column exists
    columns = [col['name'] for col in inspector.get_columns('drivers')]
    
    if 'priority_lorry_id' not in columns:
        try:
            op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(length=50), nullable=True))
            op.create_index('ix_drivers_priority_lorry_id', 'drivers', ['priority_lorry_id'])
            print("✅ Added priority_lorry_id column to drivers")
        except Exception as e:
            print(f"❌ Failed to add column: {e}")
    else:
        print("✅ priority_lorry_id column already exists")
    
    # Set this as the single head
    try:
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001_fresh_start')"))
        print("✅ Set as single migration head")
    except:
        print("⚠️  Could not set migration head")


def downgrade():
    # Cannot downgrade a fresh start
    pass