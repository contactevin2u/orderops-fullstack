
#!/usr/bin/env python


"""urgent_hotfix_trip_events_missing_columns

Revision ID: d8de5a2d905f
Revises: 2b8ae4cdc699
Create Date: 2025-09-12 18:43:52.045831

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd8de5a2d905f'
down_revision = '2b8ae4cdc699'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Urgent hotfix for trip_events missing lat, lng, note columns
    connection = op.get_bind()
    
    try:
        print("🚨 URGENT: Fixing trip_events missing columns...")
        
        # Check and add lat column
        result = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'trip_events' AND column_name = 'lat'
        """))
        
        if result.fetchone() is None:
            connection.execute(sa.text("""
                ALTER TABLE trip_events ADD COLUMN lat NUMERIC(10,6)
            """))
            print("✅ Added lat column to trip_events")
        
        # Check and add lng column
        result = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'trip_events' AND column_name = 'lng'
        """))
        
        if result.fetchone() is None:
            connection.execute(sa.text("""
                ALTER TABLE trip_events ADD COLUMN lng NUMERIC(10,6)
            """))
            print("✅ Added lng column to trip_events")
        
        # Check and add note column
        result = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'trip_events' AND column_name = 'note'
        """))
        
        if result.fetchone() is None:
            connection.execute(sa.text("""
                ALTER TABLE trip_events ADD COLUMN note TEXT
            """))
            print("✅ Added note column to trip_events")
        
        connection.commit()
        print("✅ Urgent trip_events hotfix completed successfully")
        
    except Exception as e:
        print(f"⚠️ Urgent hotfix error: {e}")
        connection.rollback()
        raise

def downgrade() -> None:
    # Remove the added columns
    connection = op.get_bind()
    
    try:
        connection.execute(sa.text("ALTER TABLE trip_events DROP COLUMN IF EXISTS note"))
        connection.execute(sa.text("ALTER TABLE trip_events DROP COLUMN IF EXISTS lng"))
        connection.execute(sa.text("ALTER TABLE trip_events DROP COLUMN IF EXISTS lat"))
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
