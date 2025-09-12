
#!/usr/bin/env python


"""add_scheduling_tables

Revision ID: 1587389fb091
Revises: 1cf733189626
Create Date: 2025-09-12 09:04:03.417961

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1587389fb091'
down_revision = '1cf733189626'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Create driver_schedules table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'driver_schedules'"))
    if not result.fetchone():
        op.create_table(
            'driver_schedules',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('schedule_date', sa.Date(), nullable=False),
            sa.Column('is_scheduled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('shift_type', sa.String(20), nullable=False, server_default='FULL_DAY'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='SCHEDULED'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_driver_schedules_driver_id', 'driver_schedules', ['driver_id'])
        op.create_index('ix_driver_schedules_schedule_date', 'driver_schedules', ['schedule_date'])
        op.create_index('ix_driver_schedules_status', 'driver_schedules', ['status'])
    
    # 2. Create driver_availability_patterns table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'driver_availability_patterns'"))
    if not result.fetchone():
        op.create_table(
            'driver_availability_patterns',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('monday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('tuesday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('wednesday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('thursday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('friday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('saturday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('sunday', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('pattern_name', sa.String(50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_driver_availability_patterns_driver_id', 'driver_availability_patterns', ['driver_id'])
        op.create_index('ix_driver_availability_patterns_is_active', 'driver_availability_patterns', ['is_active'])
    
    # 3. Create driver_shifts table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'driver_shifts'"))
    if not result.fetchone():
        op.create_table(
            'driver_shifts',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('clock_in_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('clock_in_lat', sa.Numeric(10, 6), nullable=False),
            sa.Column('clock_in_lng', sa.Numeric(10, 6), nullable=False),
            sa.Column('clock_in_location_name', sa.String(200), nullable=True),
            sa.Column('clock_out_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('clock_out_lat', sa.Numeric(10, 6), nullable=True),
            sa.Column('clock_out_lng', sa.Numeric(10, 6), nullable=True),
            sa.Column('clock_out_location_name', sa.String(200), nullable=True),
            sa.Column('is_outstation', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('outstation_distance_km', sa.Numeric(6, 2), nullable=True),
            sa.Column('outstation_allowance_amount', sa.Numeric(8, 2), nullable=False, server_default='0'),
            sa.Column('total_working_hours', sa.Numeric(4, 2), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_driver_shifts_driver_id', 'driver_shifts', ['driver_id'])
        op.create_index('ix_driver_shifts_status', 'driver_shifts', ['status'])
        op.create_index('ix_driver_shifts_clock_in_at', 'driver_shifts', ['clock_in_at'])
    
    # 4. Create lorry_stock_verifications table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'lorry_stock_verifications'"))
    if not result.fetchone():
        op.create_table(
            'lorry_stock_verifications',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('assignment_id', sa.BigInteger(), sa.ForeignKey('lorry_assignments.id'), nullable=False),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('lorry_id', sa.String(50), nullable=False),
            sa.Column('verification_date', sa.Date(), nullable=False),
            sa.Column('scanned_uids', sa.Text(), nullable=False),
            sa.Column('total_scanned', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('expected_uids', sa.Text(), nullable=True),
            sa.Column('total_expected', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('variance_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('missing_uids', sa.Text(), nullable=True),
            sa.Column('unexpected_uids', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='VERIFIED'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_lorry_stock_verifications_assignment_id', 'lorry_stock_verifications', ['assignment_id'])
        op.create_index('ix_lorry_stock_verifications_driver_id', 'lorry_stock_verifications', ['driver_id'])
        op.create_index('ix_lorry_stock_verifications_lorry_id', 'lorry_stock_verifications', ['lorry_id'])
        op.create_index('ix_lorry_stock_verifications_verification_date', 'lorry_stock_verifications', ['verification_date'])
    
    # 5. Create driver_holds table if it doesn't exist
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'driver_holds'"))
    if not result.fetchone():
        op.create_table(
            'driver_holds',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('reason', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('related_assignment_id', sa.BigInteger(), sa.ForeignKey('lorry_assignments.id'), nullable=True),
            sa.Column('related_verification_id', sa.BigInteger(), sa.ForeignKey('lorry_stock_verifications.id'), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('resolution_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_driver_holds_driver_id', 'driver_holds', ['driver_id'])
        op.create_index('ix_driver_holds_status', 'driver_holds', ['status'])
        op.create_index('ix_driver_holds_created_by', 'driver_holds', ['created_by'])
    
    # 6. Update lorry_assignments table to add shift_id FK if column missing
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'lorry_assignments' AND column_name = 'shift_id'
    """))
    if not result.fetchone():
        # Check if lorry_assignments table exists first
        table_exists = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'lorry_assignments'"))
        if table_exists.fetchone():
            op.add_column('lorry_assignments', sa.Column('shift_id', sa.BigInteger(), sa.ForeignKey('driver_shifts.id'), nullable=True))
            op.create_index('ix_lorry_assignments_shift_id', 'lorry_assignments', ['shift_id'])

def downgrade() -> None:
    connection = op.get_bind()
    
    # Drop tables in reverse order (child first, then parent)
    tables_to_drop = [
        ('driver_holds', ['ix_driver_holds_created_by', 'ix_driver_holds_status', 'ix_driver_holds_driver_id']),
        ('lorry_stock_verifications', ['ix_lorry_stock_verifications_verification_date', 'ix_lorry_stock_verifications_lorry_id', 'ix_lorry_stock_verifications_driver_id', 'ix_lorry_stock_verifications_assignment_id']),
        ('driver_shifts', ['ix_driver_shifts_clock_in_at', 'ix_driver_shifts_status', 'ix_driver_shifts_driver_id']),
        ('driver_availability_patterns', ['ix_driver_availability_patterns_is_active', 'ix_driver_availability_patterns_driver_id']),
        ('driver_schedules', ['ix_driver_schedules_status', 'ix_driver_schedules_schedule_date', 'ix_driver_schedules_driver_id']),
    ]
    
    # Remove shift_id column from lorry_assignments if it exists
    try:
        result = connection.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'lorry_assignments' AND column_name = 'shift_id'
        """))
        if result.fetchone():
            op.drop_index('ix_lorry_assignments_shift_id', 'lorry_assignments')
            op.drop_column('lorry_assignments', 'shift_id')
    except:
        pass  # Column might not exist
    
    for table_name, indexes in tables_to_drop:
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"))
        if result.fetchone():
            # Drop indexes first
            for index_name in indexes:
                try:
                    op.drop_index(index_name, table_name)
                except:
                    pass  # Index might not exist
            # Drop table
            op.drop_table(table_name)
