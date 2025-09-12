
#!/usr/bin/env python


"""create_drivers_tables

Revision ID: 207521dbe155
Revises: 8774c11f21a3
Create Date: 2025-09-12 08:52:45.811856

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '207521dbe155'
down_revision = '8774c11f21a3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create drivers table if it doesn't exist
    connection = op.get_bind()
    
    # Check if drivers table exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'drivers'
    """))
    
    if not result.fetchone():
        op.create_table(
            'drivers',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(100), nullable=True),
            sa.Column('phone', sa.String(20), nullable=True),
            sa.Column('firebase_uid', sa.String(128), nullable=False, unique=True),
            sa.Column('base_warehouse', sa.String(20), nullable=False, default='BATU_CAVES'),
            sa.Column('priority_lorry_id', sa.String(50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        
        # Create indexes for drivers table
        op.create_index('ix_drivers_phone', 'drivers', ['phone'])
        op.create_index('ix_drivers_firebase_uid', 'drivers', ['firebase_uid'])
        op.create_index('ix_drivers_priority_lorry_id', 'drivers', ['priority_lorry_id'])
    
    # Check if driver_devices table exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'driver_devices'
    """))
    
    if not result.fetchone():
        op.create_table(
            'driver_devices',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('token', sa.String(255), nullable=False),
            sa.Column('platform', sa.String(20), nullable=False),
            sa.Column('app_version', sa.String(20), nullable=True),
            sa.Column('model', sa.String(100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        
        # Create indexes for driver_devices table
        op.create_index('ix_driver_devices_driver_id', 'driver_devices', ['driver_id'])
        op.create_index('ix_driver_devices_token', 'driver_devices', ['token'])
        
        # Create unique constraint
        op.create_unique_constraint('uq_driver_devices_driver_id_token', 'driver_devices', ['driver_id', 'token'])

def downgrade() -> None:
    # Drop tables in reverse order (child first, then parent)
    connection = op.get_bind()
    
    # Drop driver_devices table if it exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'driver_devices'
    """))
    
    if result.fetchone():
        op.drop_constraint('uq_driver_devices_driver_id_token', 'driver_devices', type_='unique')
        op.drop_index('ix_driver_devices_token', 'driver_devices')
        op.drop_index('ix_driver_devices_driver_id', 'driver_devices')
        op.drop_table('driver_devices')
    
    # Drop drivers table if it exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'drivers'
    """))
    
    if result.fetchone():
        op.drop_index('ix_drivers_priority_lorry_id', 'drivers')
        op.drop_index('ix_drivers_firebase_uid', 'drivers')
        op.drop_index('ix_drivers_phone', 'drivers')
        op.drop_table('drivers')
