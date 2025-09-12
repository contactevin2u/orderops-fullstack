
#!/usr/bin/env python


"""create_routes_table

Revision ID: 8636cff57ace
Revises: 207521dbe155
Create Date: 2025-09-12 08:56:21.865133

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8636cff57ace'
down_revision = '207521dbe155'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create driver_routes table if it doesn't exist
    connection = op.get_bind()
    
    # Check if driver_routes table exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'driver_routes'
    """))
    
    if not result.fetchone():
        op.create_table(
            'driver_routes',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('route_date', sa.Date(), nullable=False),
            sa.Column('name', sa.String(60), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        
        # Create indexes for driver_routes table
        op.create_index('ix_driver_routes_driver_id', 'driver_routes', ['driver_id'])
        op.create_index('ix_driver_routes_route_date', 'driver_routes', ['route_date'])

def downgrade() -> None:
    # Drop driver_routes table if it exists
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'driver_routes'
    """))
    
    if result.fetchone():
        # Drop indexes first
        op.drop_index('ix_driver_routes_route_date', 'driver_routes')
        op.drop_index('ix_driver_routes_driver_id', 'driver_routes')
        
        # Drop table
        op.drop_table('driver_routes')
