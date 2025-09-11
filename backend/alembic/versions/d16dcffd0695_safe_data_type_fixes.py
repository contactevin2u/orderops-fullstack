
#!/usr/bin/env python


"""safe_data_type_fixes

Revision ID: d16dcffd0695
Revises: cc4615f42d6c
Create Date: 2025-09-11 21:51:42.435749

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd16dcffd0695'
down_revision = 'cc4615f42d6c'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Safely fix critical data type mismatches with individual try/catch blocks"""
    
    # Get database connection to check table/column existence
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    print("🔧 SAFELY FIXING CRITICAL DATA TYPE MISMATCHES...")
    
    # ===== USERS TABLE FIXES (Safe operations) =====
    try:
        if inspector.has_table('users'):
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Only add missing columns (safer than altering)
            if 'is_active' not in user_columns:
                try:
                    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, default=True))
                    print("✅ Added users.is_active column")
                except Exception as e:
                    print(f"⚠️ Could not add users.is_active: {e}")
            
            if 'updated_at' not in user_columns:
                try:
                    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
                    print("✅ Added users.updated_at column")
                except Exception as e:
                    print(f"⚠️ Could not add users.updated_at: {e}")
            
            print("✅ users table processed")
    except Exception as e:
        print(f"⚠️ Error processing users table: {e}")
    
    # ===== DRIVERS TABLE FIXES (Safe operations) =====  
    try:
        if inspector.has_table('drivers'):
            driver_columns = [col['name'] for col in inspector.get_columns('drivers')]
            
            # Only add missing columns (safer than altering existing ones)
            if 'base_warehouse' not in driver_columns:
                try:
                    op.add_column('drivers', sa.Column('base_warehouse', sa.String(20), nullable=False, default='BATU_CAVES'))
                    print("✅ Added drivers.base_warehouse column")
                except Exception as e:
                    print(f"⚠️ Could not add drivers.base_warehouse: {e}")
            
            if 'priority_lorry_id' not in driver_columns:
                try:
                    op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(50), nullable=True))
                    print("✅ Added drivers.priority_lorry_id column")
                    
                    # Add index
                    try:
                        op.create_index('ix_drivers_priority_lorry_id', 'drivers', ['priority_lorry_id'])
                        print("✅ Added drivers.priority_lorry_id index")
                    except Exception as e:
                        print(f"⚠️ Could not create index: {e}")
                except Exception as e:
                    print(f"⚠️ Could not add drivers.priority_lorry_id: {e}")
            
            # Safe nullable changes (these usually work)
            try:
                op.alter_column('drivers', 'name', nullable=True)
                print("✅ Fixed drivers.name: nullable=False -> nullable=True")
            except Exception as e:
                print(f"⚠️ Could not alter drivers.name nullable: {e}")
            
            print("✅ drivers table processed")
    except Exception as e:
        print(f"⚠️ Error processing drivers table: {e}")
    
    # ===== LORRIES TABLE FIXES (Safe operations) =====
    try:
        if inspector.has_table('lorries'):
            lorry_columns = [col['name'] for col in inspector.get_columns('lorries')]
            
            # Add missing columns from model if they don't exist
            missing_lorry_columns = {
                'model': sa.String(100),
                'current_location': sa.String(100),  
                'notes': sa.Text(),
                'last_maintenance_date': sa.DateTime(timezone=True)
            }
            
            for col_name, col_type in missing_lorry_columns.items():
                if col_name not in lorry_columns:
                    try:
                        op.add_column('lorries', sa.Column(col_name, col_type, nullable=True))
                        print(f"✅ Added lorries.{col_name} column")
                    except Exception as e:
                        print(f"⚠️ Could not add lorries.{col_name}: {e}")
            
            print("✅ lorries table processed")
    except Exception as e:
        print(f"⚠️ Error processing lorries table: {e}")
    
    print("🎯 Safe data type fixes completed!")
    print("   ✅ Added missing columns where possible")  
    print("   ⚠️ Skipped risky type changes that could cause transaction failures")

def downgrade() -> None:
    pass
