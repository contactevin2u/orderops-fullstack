
#!/usr/bin/env python


"""create_sku_table

Revision ID: 2135314211c2
Revises: b5f03f04bdb8
Create Date: 2025-09-12 08:43:10.561459

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2135314211c2'
down_revision = 'b5f03f04bdb8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create SKU table if it doesn't exist
    connection = op.get_bind()
    
    # Check if sku table exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'sku'
    """))
    
    if not result.fetchone():
        op.create_table(
            'sku',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('code', sa.String(100), nullable=False, unique=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('category', sa.String(50), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_serialized', sa.Boolean(), nullable=False, default=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )
        
        # Create indexes
        op.create_index('ix_sku_code', 'sku', ['code'])
        op.create_index('ix_sku_category', 'sku', ['category'])
        op.create_index('ix_sku_is_active', 'sku', ['is_active'])

def downgrade() -> None:
    # Drop SKU table and indexes if they exist
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'sku'
    """))
    
    if result.fetchone():
        # Drop indexes first
        op.drop_index('ix_sku_is_active', 'sku')
        op.drop_index('ix_sku_category', 'sku')
        op.drop_index('ix_sku_code', 'sku')
        
        # Drop table
        op.drop_table('sku')
