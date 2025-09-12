
#!/usr/bin/env python


"""hotfix_driver_shifts_total_working_hours

Revision ID: 16b7d5977eb6
Revises: 2e273258bc37
Create Date: 2025-09-12 17:51:43.119144

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '16b7d5977eb6'
down_revision = '2e273258bc37'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # URGENT HOTFIX: Add total_working_hours column if missing
    # This is a critical fix for driver clock-in functionality
    
    connection = op.get_bind()
    
    # Check if column exists
    try:
        result = connection.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'driver_shifts' 
            AND column_name = 'total_working_hours'
        """))
        
        if result.fetchone() is None:
            # Column doesn't exist, add it
            connection.execute(sa.text("""
                ALTER TABLE driver_shifts 
                ADD COLUMN total_working_hours NUMERIC(4,2)
            """))
            print("✅ HOTFIX: Added total_working_hours column to driver_shifts")
        else:
            print("✅ HOTFIX: total_working_hours column already exists")
            
        # Also check for other critical missing columns
        critical_columns = [
            ('is_outstation', 'BOOLEAN DEFAULT FALSE'),
            ('outstation_distance_km', 'NUMERIC(6,2)'),  
            ('outstation_allowance_amount', 'NUMERIC(8,2) DEFAULT 0'),
            ('status', "VARCHAR(20) DEFAULT 'ACTIVE'"),
            ('notes', 'TEXT'),
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
        ]
        
        for col_name, col_def in critical_columns:
            result = connection.execute(sa.text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'driver_shifts' 
                AND column_name = '{col_name}'
            """))
            
            if result.fetchone() is None:
                connection.execute(sa.text(f"""
                    ALTER TABLE driver_shifts 
                    ADD COLUMN {col_name} {col_def}
                """))
                print(f"✅ HOTFIX: Added {col_name} column to driver_shifts")
                
        connection.commit()
        
    except Exception as e:
        print(f"⚠️  HOTFIX Error: {e}")
        connection.rollback()

def downgrade() -> None:
    # Remove the hotfix columns
    connection = op.get_bind()
    
    columns_to_remove = [
        'total_working_hours', 'is_outstation', 'outstation_distance_km',
        'outstation_allowance_amount', 'status', 'notes', 'created_at', 'updated_at'
    ]
    
    for col_name in columns_to_remove:
        try:
            connection.execute(sa.text(f"ALTER TABLE driver_shifts DROP COLUMN IF EXISTS {col_name}"))
        except:
            pass  # Ignore errors if column doesn't exist
