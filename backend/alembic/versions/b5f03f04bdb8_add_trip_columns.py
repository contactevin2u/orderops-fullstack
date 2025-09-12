
#!/usr/bin/env python


"""add_trip_columns

Revision ID: b5f03f04bdb8
Revises: 2cdfa4145df8
Create Date: 2025-09-12 08:36:17.584904

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b5f03f04bdb8'
down_revision = '2cdfa4145df8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add missing columns to trips table if they don't exist
    connection = op.get_bind()
    
    # Define columns that might be missing from trips table
    trip_columns = [
        ('planned_at', sa.Column('planned_at', sa.DateTime(timezone=True), nullable=True)),
        ('started_at', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True)),
        ('delivered_at', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True)),
        ('failure_reason', sa.Column('failure_reason', sa.Text(), nullable=True)),
        ('pod_photo_url', sa.Column('pod_photo_url', sa.Text(), nullable=True)),
        ('pod_photo_url_1', sa.Column('pod_photo_url_1', sa.Text(), nullable=True)),
        ('pod_photo_url_2', sa.Column('pod_photo_url_2', sa.Text(), nullable=True)),
        ('pod_photo_url_3', sa.Column('pod_photo_url_3', sa.Text(), nullable=True)),
        ('payment_method', sa.Column('payment_method', sa.String(30), nullable=True)),
        ('payment_reference', sa.Column('payment_reference', sa.String(50), nullable=True)),
    ]
    
    for col_name, column_def in trip_columns:
        result = connection.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trips' AND column_name = '{col_name}'
        """))
        
        if not result.fetchone():
            op.add_column('trips', column_def)

def downgrade() -> None:
    # Drop trip columns in reverse order if they exist
    connection = op.get_bind()
    
    columns_to_drop = [
        'payment_reference', 'payment_method', 'pod_photo_url_3', 
        'pod_photo_url_2', 'pod_photo_url_1', 'pod_photo_url',
        'failure_reason', 'delivered_at', 'started_at', 'planned_at'
    ]
    
    for col_name in columns_to_drop:
        result = connection.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trips' AND column_name = '{col_name}'
        """))
        
        if result.fetchone():
            op.drop_column('trips', col_name)
