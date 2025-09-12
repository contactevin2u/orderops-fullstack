
#!/usr/bin/env python


"""comprehensive_schema_fix_all_missing_columns

Revision ID: e1aeda899276
Revises: ccbccb165e0a
Create Date: 2025-09-12 17:59:27.399300

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1aeda899276'
down_revision = 'ccbccb165e0a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Comprehensive fix for all database schema issues to prevent API errors
    connection = op.get_bind()
    
    try:
        # Fix audit_logs table
        print("🔧 Checking audit_logs table...")
        result = connection.execute(sa.text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'audit_logs'
        """))
        
        if result.fetchone() is None:
            connection.execute(sa.text("""
                CREATE TABLE audit_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action VARCHAR(100) NOT NULL,
                    details JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            print("✅ Created audit_logs table")
        
        # Fix driver_shifts table - add all missing columns
        print("🔧 Checking driver_shifts table...")
        driver_shifts_columns = [
            ('is_outstation', 'BOOLEAN DEFAULT FALSE'),
            ('outstation_distance_km', 'NUMERIC(6,2)'),  
            ('outstation_allowance_amount', 'NUMERIC(8,2) DEFAULT 0'),
            ('total_working_hours', 'NUMERIC(4,2)'),
            ('status', "VARCHAR(20) DEFAULT 'ACTIVE'"),
            ('notes', 'TEXT'),
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('clock_in_location_name', 'VARCHAR(200)'),
            ('clock_out_location_name', 'VARCHAR(200)')
        ]
        
        for col_name, col_def in driver_shifts_columns:
            result = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'driver_shifts' AND column_name = '{col_name}'
            """))
            
            if result.fetchone() is None:
                connection.execute(sa.text(f"""
                    ALTER TABLE driver_shifts ADD COLUMN {col_name} {col_def}
                """))
                print(f"✅ Added {col_name} to driver_shifts")
        
        # Fix sku table - add all missing columns  
        print("🔧 Checking sku table...")
        sku_columns = [
            ('code', 'VARCHAR(100)'),
            ('name', 'VARCHAR(200) NOT NULL DEFAULT \'Unknown SKU\''),
            ('category', 'VARCHAR(50)'),
            ('description', 'TEXT'),
            ('is_serialized', 'BOOLEAN DEFAULT FALSE'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
        ]
        
        # Check if sku table exists
        result = connection.execute(sa.text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'sku'
        """))
        
        if result.fetchone() is not None:
            for col_name, col_def in sku_columns:
                result = connection.execute(sa.text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'sku' AND column_name = '{col_name}'
                """))
                
                if result.fetchone() is None:
                    connection.execute(sa.text(f"""
                        ALTER TABLE sku ADD COLUMN {col_name} {col_def}
                    """))
                    print(f"✅ Added {col_name} to sku")
            
            # Populate code column if it was just added
            result = connection.execute(sa.text("""
                SELECT COUNT(*) FROM sku WHERE code IS NULL
            """))
            null_count = result.scalar()
            
            if null_count > 0:
                connection.execute(sa.text("""
                    UPDATE sku SET code = 'SKU' || LPAD(id::text, 6, '0') 
                    WHERE code IS NULL
                """))
                print(f"✅ Populated {null_count} missing SKU codes")
        
        # Fix idempotent_requests table - critical for void orders
        print("🔧 Checking idempotent_requests table...")
        result = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'idempotent_requests' AND column_name = 'id'
        """))
        
        if result.fetchone() is None:
            # Missing primary key - recreate table with correct structure
            print("⚠️ idempotent_requests table missing id column, recreating...")
            connection.execute(sa.text("""
                DROP TABLE IF EXISTS idempotent_requests CASCADE
            """))
            connection.execute(sa.text("""
                CREATE TABLE idempotent_requests (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    order_id INTEGER REFERENCES orders(id),
                    action VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            print("✅ Recreated idempotent_requests table with correct schema")
        
        connection.commit()
        print("✅ Comprehensive schema fix completed successfully")
        
    except Exception as e:
        print(f"⚠️ Schema fix error: {e}")
        connection.rollback()
        raise


def downgrade() -> None:
    # Reverse the comprehensive schema fixes
    connection = op.get_bind()
    
    try:
        # Remove added columns from driver_shifts
        columns_to_remove = [
            'clock_out_location_name', 'clock_in_location_name', 'updated_at', 
            'created_at', 'notes', 'status', 'total_working_hours',
            'outstation_allowance_amount', 'outstation_distance_km', 'is_outstation'
        ]
        
        for col in columns_to_remove:
            connection.execute(sa.text(f"ALTER TABLE driver_shifts DROP COLUMN IF EXISTS {col}"))
        
        # Remove added columns from sku  
        sku_columns_to_remove = [
            'updated_at', 'created_at', 'is_active', 'is_serialized',
            'description', 'category', 'name', 'code'
        ]
        
        for col in sku_columns_to_remove:
            connection.execute(sa.text(f"ALTER TABLE sku DROP COLUMN IF EXISTS {col}"))
        
        # Drop audit_logs table
        connection.execute(sa.text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
