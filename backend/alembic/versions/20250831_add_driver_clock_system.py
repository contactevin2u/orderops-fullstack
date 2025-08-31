"""Add DriverShift and CommissionEntry models for clock-in/clock-out system

Revision ID: 20250831_clock_system
Revises: previous_revision
Create Date: 2025-08-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250831_clock_system'
down_revision = None  # Update this with the actual latest revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create driver_shifts table
    op.create_table('driver_shifts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.BigInteger(), nullable=False),
        sa.Column('clock_in_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('clock_in_lat', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('clock_in_lng', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('clock_in_location_name', sa.String(length=200), nullable=True),
        sa.Column('clock_out_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clock_out_lat', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('clock_out_lng', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('clock_out_location_name', sa.String(length=200), nullable=True),
        sa.Column('is_outstation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('outstation_distance_km', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('outstation_allowance_amount', sa.Numeric(precision=8, scale=2), nullable=False, server_default='0'),
        sa.Column('total_working_hours', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_driver_shifts_driver_id'), 'driver_shifts', ['driver_id'], unique=False)

    # Create commission_entries table
    op.create_table('commission_entries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.BigInteger(), nullable=False),
        sa.Column('shift_id', sa.BigInteger(), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=True),
        sa.Column('trip_id', sa.BigInteger(), nullable=True),
        sa.Column('entry_type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('driver_role', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='EARNED'),
        sa.Column('base_commission_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('order_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('commission_scheme', sa.String(length=50), nullable=True),
        sa.Column('earned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['shift_id'], ['driver_shifts.id'], ),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commission_entries_driver_id'), 'commission_entries', ['driver_id'], unique=False)
    op.create_index(op.f('ix_commission_entries_order_id'), 'commission_entries', ['order_id'], unique=False)
    op.create_index(op.f('ix_commission_entries_shift_id'), 'commission_entries', ['shift_id'], unique=False)
    op.create_index(op.f('ix_commission_entries_trip_id'), 'commission_entries', ['trip_id'], unique=False)


def downgrade() -> None:
    # Drop commission_entries table
    op.drop_index(op.f('ix_commission_entries_trip_id'), table_name='commission_entries')
    op.drop_index(op.f('ix_commission_entries_shift_id'), table_name='commission_entries')
    op.drop_index(op.f('ix_commission_entries_order_id'), table_name='commission_entries')
    op.drop_index(op.f('ix_commission_entries_driver_id'), table_name='commission_entries')
    op.drop_table('commission_entries')
    
    # Drop driver_shifts table
    op.drop_index(op.f('ix_driver_shifts_driver_id'), table_name='driver_shifts')
    op.drop_table('driver_shifts')