
#!/usr/bin/env python


"""fix_critical_data_type_mismatches

Revision ID: cc4615f42d6c
Revises: e11dbc008f13
Create Date: 2025-09-11 21:49:33.848425

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cc4615f42d6c'
down_revision = 'e11dbc008f13'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """DISABLED: Fix critical data type mismatches between models and database schema"""
    
    print("⚠️ This migration has been disabled due to transaction issues.")
    print("✅ Using safer migration d16dcffd0695_safe_data_type_fixes instead.")
    return  # Skip this migration
    
    # Get database connection to check table/column existence
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    print("🔧 FIXING CRITICAL DATA TYPE MISMATCHES...")
    
    # ===== USERS TABLE FIXES =====
    if inspector.has_table('users'):
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Fix users.password_hash length: String(255) -> String(128) to match model
        if 'password_hash' in user_columns:
            op.alter_column('users', 'password_hash', type_=sa.String(128))
            print("✅ Fixed users.password_hash: String(255) -> String(128)")
        
        # Fix users.role: String(20) -> Enum but keep as String for compatibility
        # Note: Role enum values are ADMIN, CASHIER, DRIVER (all fit in String(20))
        print("✅ users.role: String(20) compatible with Enum(Role)")
        
        # Add missing columns if they don't exist
        if 'is_active' not in user_columns:
            op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, default=True))
            print("✅ Added users.is_active column")
        
        if 'updated_at' not in user_columns:
            op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
            print("✅ Added users.updated_at column")
    
    # ===== DRIVERS TABLE FIXES =====  
    if inspector.has_table('drivers'):
        driver_columns = [col['name'] for col in inspector.get_columns('drivers')]
        
        # Fix drivers.id: Integer -> BigInteger to match model
        op.alter_column('drivers', 'id', type_=sa.BigInteger())
        print("✅ Fixed drivers.id: Integer -> BigInteger")
        
        # Fix drivers.name: nullable=False -> nullable=True to match model
        op.alter_column('drivers', 'name', nullable=True)
        print("✅ Fixed drivers.name: nullable=False -> nullable=True")
        
        # Fix drivers.phone: String(50) -> String(20) to match model
        op.alter_column('drivers', 'phone', type_=sa.String(20))
        print("✅ Fixed drivers.phone: String(50) -> String(20)")
        
        # Fix drivers.firebase_uid: nullable=True -> nullable=False to match model
        op.alter_column('drivers', 'firebase_uid', nullable=False)
        print("✅ Fixed drivers.firebase_uid: nullable=True -> nullable=False")
        
        # Add missing columns if they don't exist
        if 'base_warehouse' not in driver_columns:
            op.add_column('drivers', sa.Column('base_warehouse', sa.String(20), nullable=False, default='BATU_CAVES'))
            print("✅ Added drivers.base_warehouse column")
        
        if 'priority_lorry_id' not in driver_columns:
            op.add_column('drivers', sa.Column('priority_lorry_id', sa.String(50), nullable=True))
            op.create_index('ix_drivers_priority_lorry_id', 'drivers', ['priority_lorry_id'])
            print("✅ Added drivers.priority_lorry_id column with index")
    
    # ===== LORRIES TABLE FIXES =====
    # Check if specialized tables migration created lorries table correctly
    if inspector.has_table('lorries'):
        lorry_columns = [col['name'] for col in inspector.get_columns('lorries')]
        
        # The lorries table from specialized migration has some inconsistencies
        # Fix: lorry.name -> not in model (should be removed or mapped)
        # Fix: lorry.capacity -> Integer in migration vs String(50) in model
        if 'capacity' in lorry_columns:
            # Get current column info
            for col in inspector.get_columns('lorries'):
                if col['name'] == 'capacity' and str(col['type']).startswith('INTEGER'):
                    op.alter_column('lorries', 'capacity', type_=sa.String(50))
                    print("✅ Fixed lorries.capacity: Integer -> String(50)")
                    break
        
        # Add missing columns from model if they don't exist
        missing_lorry_columns = {
            'model': sa.String(100),
            'current_location': sa.String(100),
            'notes': sa.Text(),
            'last_maintenance_date': sa.DateTime(timezone=True)
        }
        
        for col_name, col_type in missing_lorry_columns.items():
            if col_name not in lorry_columns:
                op.add_column('lorries', sa.Column(col_name, col_type, nullable=True))
                print(f"✅ Added lorries.{col_name} column")
    
    print("🎯 Critical data type mismatches fixed!")
    print("   ✅ users table: password_hash length, missing columns")  
    print("   ✅ drivers table: ID type, field constraints, missing columns")
    print("   ✅ lorries table: capacity type, missing columns")

def downgrade() -> None:
    """Reverse the data type fixes (use with caution in production)"""
    
    print("⚠️  REVERSING DATA TYPE FIXES...")
    
    # Get database connection
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Reverse users table changes
    if inspector.has_table('users'):
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'password_hash' in user_columns:
            op.alter_column('users', 'password_hash', type_=sa.String(255))
        
        if 'is_active' in user_columns:
            op.drop_column('users', 'is_active')
        
        if 'updated_at' in user_columns:
            op.drop_column('users', 'updated_at')
    
    # Reverse drivers table changes
    if inspector.has_table('drivers'):
        driver_columns = [col['name'] for col in inspector.get_columns('drivers')]
        
        op.alter_column('drivers', 'id', type_=sa.Integer())
        op.alter_column('drivers', 'name', nullable=False)
        op.alter_column('drivers', 'phone', type_=sa.String(50))
        op.alter_column('drivers', 'firebase_uid', nullable=True)
        
        if 'base_warehouse' in driver_columns:
            op.drop_column('drivers', 'base_warehouse')
        
        if 'priority_lorry_id' in driver_columns:
            op.drop_index('ix_drivers_priority_lorry_id', 'drivers')
            op.drop_column('drivers', 'priority_lorry_id')
    
    # Reverse lorries table changes  
    if inspector.has_table('lorries'):
        lorry_columns = [col['name'] for col in inspector.get_columns('lorries')]
        
        if 'capacity' in lorry_columns:
            op.alter_column('lorries', 'capacity', type_=sa.Integer())
        
        for col_name in ['model', 'current_location', 'notes', 'last_maintenance_date']:
            if col_name in lorry_columns:
                op.drop_column('lorries', col_name)
    
    print("✅ Data type fixes reversed")
