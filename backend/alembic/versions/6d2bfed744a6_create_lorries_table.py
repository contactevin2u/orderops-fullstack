
#!/usr/bin/env python


"""create_lorries_table

Revision ID: 6d2bfed744a6
Revises: 002_add_priority_lorry_id
Create Date: 2025-09-08 16:16:13.221366

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6d2bfed744a6'
down_revision = '002_add_priority_lorry_id'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create lorries table"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if lorries table already exists
    tables = inspector.get_table_names()
    if 'lorries' in tables:
        print("✅ lorries table already exists")
        return
    
    print("🚛 Creating lorries table...")
    
    op.create_table(
        'lorries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('plate_number', sa.String(length=20), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('capacity', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('base_warehouse', sa.String(length=20), nullable=False),
        sa.Column('current_location', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_maintenance_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_lorries_lorry_id'), 'lorries', ['lorry_id'], unique=True)
    op.create_index(op.f('ix_lorries_plate_number'), 'lorries', ['plate_number'], unique=False)
    
    print("✅ Created lorries table with indexes")

def downgrade() -> None:
    """Drop lorries table"""
    op.drop_index(op.f('ix_lorries_plate_number'), 'lorries')
    op.drop_index(op.f('ix_lorries_lorry_id'), 'lorries')
    op.drop_table('lorries')
