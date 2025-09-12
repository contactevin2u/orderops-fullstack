
#!/usr/bin/env python


"""fix_upsell_table_schema

Revision ID: 9e2616b970b7
Revises: 1587389fb091
Create Date: 2025-09-12 09:10:00.984513

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9e2616b970b7'
down_revision = '1587389fb091'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if upsell_records table exists
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'upsell_records'"))
    
    if not result.fetchone():
        # Create upsell_records table with correct schema matching the model
        op.create_table('upsell_records',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('trip_id', sa.Integer(), sa.ForeignKey('trips.id'), nullable=False),
            sa.Column('original_total', sa.Numeric(12, 2), nullable=False),
            sa.Column('new_total', sa.Numeric(12, 2), nullable=False),
            sa.Column('upsell_amount', sa.Numeric(12, 2), nullable=False),
            sa.Column('items_data', sa.Text(), nullable=False),  # JSON string of upsold items
            sa.Column('upsell_notes', sa.Text(), nullable=True),
            sa.Column('driver_incentive', sa.Numeric(10, 2), nullable=False),
            sa.Column('incentive_status', sa.String(20), nullable=False, server_default='PENDING'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        )
        
        # Create indexes for performance
        op.create_index('ix_upsell_records_order_id', 'upsell_records', ['order_id'])
        op.create_index('ix_upsell_records_driver_id', 'upsell_records', ['driver_id'])
        op.create_index('ix_upsell_records_trip_id', 'upsell_records', ['trip_id'])
        op.create_index('ix_upsell_records_incentive_status', 'upsell_records', ['incentive_status'])
        op.create_index('ix_upsell_records_released_at', 'upsell_records', ['released_at'])
        op.create_index('ix_upsell_records_created_at', 'upsell_records', ['created_at'])
    else:
        # Table exists, check for missing columns and add them
        
        # Check if original_total column exists
        original_total_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'original_total'
        """)).fetchone()
        
        if not original_total_exists:
            op.add_column('upsell_records', sa.Column('original_total', sa.Numeric(12, 2), nullable=False, server_default='0'))
        
        # Check if new_total column exists
        new_total_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'new_total'
        """)).fetchone()
        
        if not new_total_exists:
            op.add_column('upsell_records', sa.Column('new_total', sa.Numeric(12, 2), nullable=False, server_default='0'))
        
        # Check if items_data column exists (might be named items_upsold in old schema)
        items_data_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'items_data'
        """)).fetchone()
        
        items_upsold_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'items_upsold'
        """)).fetchone()
        
        if not items_data_exists and items_upsold_exists:
            # Rename items_upsold to items_data
            op.alter_column('upsell_records', 'items_upsold', new_column_name='items_data')
        elif not items_data_exists and not items_upsold_exists:
            # Add items_data column
            op.add_column('upsell_records', sa.Column('items_data', sa.Text(), nullable=False, server_default='[]'))
        
        # Check if upsell_notes column exists (might be named notes)
        upsell_notes_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'upsell_notes'
        """)).fetchone()
        
        notes_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'notes'
        """)).fetchone()
        
        if not upsell_notes_exists and notes_exists:
            # Rename notes to upsell_notes
            op.alter_column('upsell_records', 'notes', new_column_name='upsell_notes')
        elif not upsell_notes_exists and not notes_exists:
            # Add upsell_notes column
            op.add_column('upsell_records', sa.Column('upsell_notes', sa.Text(), nullable=True))
        
        # Check if incentive_status column exists (might be named status)
        incentive_status_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'incentive_status'
        """)).fetchone()
        
        status_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'upsell_records' AND column_name = 'status'
        """)).fetchone()
        
        if not incentive_status_exists and status_exists:
            # Rename status to incentive_status
            op.alter_column('upsell_records', 'status', new_column_name='incentive_status')
        elif not incentive_status_exists and not status_exists:
            # Add incentive_status column
            op.add_column('upsell_records', sa.Column('incentive_status', sa.String(20), nullable=False, server_default='PENDING'))
        
        # Ensure all required indexes exist
        try:
            op.create_index('ix_upsell_records_trip_id', 'upsell_records', ['trip_id'])
        except:
            pass  # Index might already exist
        
        try:
            op.create_index('ix_upsell_records_incentive_status', 'upsell_records', ['incentive_status'])
        except:
            pass  # Index might already exist
        
        try:
            op.create_index('ix_upsell_records_released_at', 'upsell_records', ['released_at'])
        except:
            pass  # Index might already exist

def downgrade() -> None:
    connection = op.get_bind()
    
    # Check if upsell_records table exists
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'upsell_records'"))
    
    if result.fetchone():
        # Drop indexes first
        indexes_to_drop = [
            'ix_upsell_records_created_at',
            'ix_upsell_records_released_at', 
            'ix_upsell_records_incentive_status',
            'ix_upsell_records_trip_id',
            'ix_upsell_records_driver_id',
            'ix_upsell_records_order_id'
        ]
        
        for index_name in indexes_to_drop:
            try:
                op.drop_index(index_name, 'upsell_records')
            except:
                pass  # Index might not exist
        
        # Drop the table
        op.drop_table('upsell_records')
