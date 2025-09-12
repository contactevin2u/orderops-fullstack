
#!/usr/bin/env python


"""fix_trips_route_foreign_key_constraint

Revision ID: 2b8ae4cdc699
Revises: e1aeda899276
Create Date: 2025-09-12 18:23:29.647533

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2b8ae4cdc699'
down_revision = 'e1aeda899276'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Fix trips.route_id foreign key constraint to point to driver_routes instead of routes
    connection = op.get_bind()
    
    try:
        print("🔧 Fixing trips.route_id foreign key constraint...")
        
        # Drop the incorrect foreign key constraint
        connection.execute(sa.text("""
            ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_route_id_fkey
        """))
        print("✅ Dropped incorrect foreign key constraint trips_route_id_fkey")
        
        # Add the correct foreign key constraint pointing to driver_routes
        connection.execute(sa.text("""
            ALTER TABLE trips 
            ADD CONSTRAINT trips_route_id_fkey 
            FOREIGN KEY (route_id) REFERENCES driver_routes(id) ON DELETE SET NULL
        """))
        print("✅ Added correct foreign key constraint pointing to driver_routes")
        
        connection.commit()
        print("✅ Foreign key constraint fix completed successfully")
        
    except Exception as e:
        print(f"⚠️ Foreign key fix error: {e}")
        connection.rollback()
        raise


def downgrade() -> None:
    # Reverse the foreign key fix
    connection = op.get_bind()
    
    try:
        # Drop the correct foreign key constraint
        connection.execute(sa.text("""
            ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_route_id_fkey
        """))
        
        # Add back the incorrect foreign key constraint (for rollback purposes)
        connection.execute(sa.text("""
            ALTER TABLE trips 
            ADD CONSTRAINT trips_route_id_fkey 
            FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE SET NULL
        """))
        
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
