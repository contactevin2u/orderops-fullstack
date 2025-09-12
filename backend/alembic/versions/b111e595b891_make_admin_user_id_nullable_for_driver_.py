#!/usr/bin/env python


"""make_admin_user_id_nullable_for_driver_deliveries

Revision ID: b111e595b891
Revises: 857b8e0d691c
Create Date: 2025-09-12 21:15:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b111e595b891'
down_revision = '857b8e0d691c'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Make admin_user_id nullable for driver deliveries
    connection = op.get_bind()
    
    try:
        print("🔧 Making admin_user_id nullable for driver deliveries...")
        
        # Make the column nullable
        connection.execute(sa.text("""
            ALTER TABLE lorry_stock_transactions 
            ALTER COLUMN admin_user_id DROP NOT NULL
        """))
        
        print("✅ admin_user_id column is now nullable")
        connection.commit()
        
    except Exception as e:
        print(f"⚠️ Migration error: {e}")
        connection.rollback()
        raise

def downgrade() -> None:
    # Revert admin_user_id to NOT NULL
    connection = op.get_bind()
    
    try:
        # First, update any NULL values to a default admin user ID
        connection.execute(sa.text("""
            UPDATE lorry_stock_transactions 
            SET admin_user_id = 1 
            WHERE admin_user_id IS NULL
        """))
        
        # Then make the column NOT NULL again
        connection.execute(sa.text("""
            ALTER TABLE lorry_stock_transactions 
            ALTER COLUMN admin_user_id SET NOT NULL
        """))
        
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
        raise