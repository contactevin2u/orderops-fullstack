"""Add priority_lorry_id column after ghost revisions

Revision ID: 002_add_priority_lorry_id
Revises: 20250908_stock_txns
Create Date: 2025-09-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '002_add_priority_lorry_id'
down_revision = '20250908_stock_txns'
branch_labels = None
depends_on = None


def upgrade():
    """Add the missing priority_lorry_id column"""
    print("🎯 Adding priority_lorry_id column...")
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if drivers table exists
    tables = inspector.get_table_names()
    if 'drivers' not in tables:
        print("❌ drivers table doesn't exist")
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


def downgrade():
    try:
        op.drop_index('ix_drivers_priority_lorry_id', 'drivers')
        op.drop_column('drivers', 'priority_lorry_id')
    except:
        pass