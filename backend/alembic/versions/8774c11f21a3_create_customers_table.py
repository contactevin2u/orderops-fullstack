
#!/usr/bin/env python


"""create_customers_table

Revision ID: 8774c11f21a3
Revises: 2135314211c2
Create Date: 2025-09-12 08:46:20.210948

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8774c11f21a3'
down_revision = '2135314211c2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create customers table if it doesn't exist
    connection = op.get_bind()
    
    # Check if customers table exists
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'customers'
    """))
    
    if not result.fetchone():
        op.create_table(
            'customers',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('phone', sa.String(50), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('map_url', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        
        # Create indexes
        op.create_index('ix_customers_phone', 'customers', ['phone'])

def downgrade() -> None:
    # Drop customers table if it exists
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'customers'
    """))
    
    if result.fetchone():
        # Drop index first
        op.drop_index('ix_customers_phone', 'customers')
        
        # Drop table
        op.drop_table('customers')
