
#!/usr/bin/env python


"""add dual driver support to trips

Revision ID: f36d7abf49c7
Revises: 0012
Create Date: 2025-08-30 21:40:31.751739

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f36d7abf49c7'
down_revision = '0012'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add optional second driver to trips
    op.add_column('trips', sa.Column('driver_id_2', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=True))
    
    # Remove unique constraint on commission.trip_id to allow multiple commissions per trip
    op.drop_constraint('commissions_trip_id_key', 'commissions', type_='unique')
    
    # Add index for the new driver_id_2 column
    op.create_index('ix_trips_driver_id_2', 'trips', ['driver_id_2'])
    
def downgrade() -> None:
    # Remove the index
    op.drop_index('ix_trips_driver_id_2', 'trips')
    
    # Re-add unique constraint on commission.trip_id
    op.create_unique_constraint('commissions_trip_id_key', 'commissions', ['trip_id'])
    
    # Remove driver_id_2 column
    op.drop_column('trips', 'driver_id_2')
