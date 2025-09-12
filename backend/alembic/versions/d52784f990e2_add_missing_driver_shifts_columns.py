
#!/usr/bin/env python


"""add_missing_driver_shifts_columns

Revision ID: d52784f990e2
Revises: 62fb995d6d46
Create Date: 2025-09-12 17:31:14.329973

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd52784f990e2'
down_revision = '62fb995d6d46'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if driver_shifts table exists and what columns it has
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('driver_shifts'):
        columns = [col['name'] for col in inspector.get_columns('driver_shifts')]
        print(f"Current driver_shifts columns: {columns}")
        
        # Add missing outstation tracking columns
        missing_columns = []
        
        if 'is_outstation' not in columns:
            op.add_column('driver_shifts', 
                sa.Column('is_outstation', sa.Boolean(), nullable=False, server_default=sa.text('false'))
            )
            missing_columns.append('is_outstation')
        
        if 'outstation_distance_km' not in columns:
            op.add_column('driver_shifts', 
                sa.Column('outstation_distance_km', sa.Numeric(6, 2), nullable=True)
            )
            missing_columns.append('outstation_distance_km')
            
        if 'outstation_allowance_amount' not in columns:
            op.add_column('driver_shifts', 
                sa.Column('outstation_allowance_amount', sa.Numeric(8, 2), nullable=False, server_default=sa.text('0'))
            )
            missing_columns.append('outstation_allowance_amount')
        
        if missing_columns:
            print(f"✅ Added missing columns to driver_shifts: {missing_columns}")
        else:
            print("✅ driver_shifts table already has all required columns")
    else:
        print("⚠️ driver_shifts table doesn't exist - this shouldn't happen")

def downgrade() -> None:
    # Remove the added columns
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('driver_shifts'):
        columns = [col['name'] for col in inspector.get_columns('driver_shifts')]
        
        if 'outstation_allowance_amount' in columns:
            op.drop_column('driver_shifts', 'outstation_allowance_amount')
        if 'outstation_distance_km' in columns:
            op.drop_column('driver_shifts', 'outstation_distance_km')
        if 'is_outstation' in columns:
            op.drop_column('driver_shifts', 'is_outstation')
            
        print("✅ Removed outstation columns from driver_shifts")
