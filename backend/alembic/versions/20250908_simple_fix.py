"""Simple fix: Add priority_lorry_id to drivers

Revision ID: 20250908_simple_fix
Revises: 3c8b1c03e2ca
Create Date: 2025-09-08 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250908_simple_fix'
down_revision = '3c8b1c03e2ca'
branch_labels = None
depends_on = None


def upgrade():
    # Simple: just add the missing column
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if column exists
    try:
        columns = [col['name'] for col in inspector.get_columns('drivers')]
        if 'priority_lorry_id' not in columns:
            op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(length=50), nullable=True))
            op.create_index('ix_drivers_priority_lorry_id', 'drivers', ['priority_lorry_id'])
            print("✅ Added priority_lorry_id column")
        else:
            print("✅ priority_lorry_id already exists")
    except Exception as e:
        print(f"⚠️  Column check failed: {e}")
        # Try to add anyway
        try:
            op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(length=50), nullable=True))
            op.create_index('ix_drivers_priority_lorry_id', 'drivers', ['priority_lorry_id'])
            print("✅ Added priority_lorry_id column (fallback)")
        except:
            print("✅ Column probably already exists")


def downgrade():
    try:
        op.drop_index('ix_drivers_priority_lorry_id', 'drivers')
        op.drop_column('drivers', 'priority_lorry_id')
    except:
        pass