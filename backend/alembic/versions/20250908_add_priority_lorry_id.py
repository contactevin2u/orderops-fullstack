"""Add priority_lorry_id to drivers table

Revision ID: 20250908_add_priority_lorry_id
Revises: 3c8b1c03e2ca
Create Date: 2025-09-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250908_add_priority_lorry_id'
down_revision = '3c8b1c03e2ca'
branch_labels = None
depends_on = None


def upgrade():
    # Get database connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if priority_lorry_id column already exists
    existing_columns = [col['name'] for col in inspector.get_columns('drivers')]
    
    if 'priority_lorry_id' not in existing_columns:
        # Add priority_lorry_id to drivers table
        op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(length=50), nullable=True))
        op.create_index(op.f('ix_drivers_priority_lorry_id'), 'drivers', ['priority_lorry_id'], unique=False)
        print("✅ Added priority_lorry_id column to drivers table")
    else:
        print("✅ priority_lorry_id column already exists - skipping")


def downgrade():
    # Check if column exists before trying to drop it
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('drivers')]
    
    if 'priority_lorry_id' in existing_columns:
        op.drop_index(op.f('ix_drivers_priority_lorry_id'), table_name='drivers')
        op.drop_column('drivers', 'priority_lorry_id')