#!/usr/bin/env python

"""add_map_url_to_customers

Revision ID: b2f8e4a6d1c3
Revises: ea3164c6b3f5
Create Date: 2025-09-12 10:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2f8e4a6d1c3'
down_revision = 'ea3164c6b3f5'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if customers table exists
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'customers'"))
    if result.fetchone():
        
        # Add map_url column if it doesn't exist
        map_url_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'customers' AND column_name = 'map_url'
        """)).fetchone()
        
        if not map_url_exists:
            op.add_column('customers', sa.Column('map_url', sa.Text(), nullable=True))
            print("✅ Added map_url column to customers table")
        else:
            print("✅ map_url column already exists in customers table")
    else:
        print("⚠️ Customers table doesn't exist - creating it")
        op.create_table('customers',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('map_url', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_customers_phone'), 'customers', ['phone'], unique=False)
        print("✅ Created customers table with map_url column")

def downgrade() -> None:
    connection = op.get_bind()
    
    # Check if customers table exists
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'customers'"))
    if result.fetchone():
        
        # Remove map_url column if it exists
        map_url_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'customers' AND column_name = 'map_url'
        """)).fetchone()
        
        if map_url_exists:
            op.drop_column('customers', 'map_url')
            print("✅ Removed map_url column from customers table")
        else:
            print("✅ map_url column doesn't exist in customers table")
    else:
        print("⚠️ Customers table doesn't exist - nothing to rollback")