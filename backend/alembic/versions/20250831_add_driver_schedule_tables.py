"""Add driver schedule and availability pattern tables

Revision ID: 20250831_schedule_tables
Revises: 20250831_clock_system
Create Date: 2025-08-31 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250831_schedule_tables'
down_revision = '20250831_clock_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create driver_schedules table
    op.create_table('driver_schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('schedule_date', sa.Date(), nullable=False),
        sa.Column('is_scheduled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('shift_type', sa.String(length=20), nullable=False, server_default='FULL_DAY'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='SCHEDULED'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_driver_schedules_driver_id'), 'driver_schedules', ['driver_id'], unique=False)
    op.create_index(op.f('ix_driver_schedules_schedule_date'), 'driver_schedules', ['schedule_date'], unique=False)
    op.create_index(op.f('ix_driver_schedules_driver_date'), 'driver_schedules', ['driver_id', 'schedule_date'], unique=True)

    # Create driver_availability_patterns table
    op.create_table('driver_availability_patterns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('monday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tuesday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('wednesday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('thursday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('friday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('saturday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sunday', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('pattern_name', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_driver_availability_patterns_driver_id'), 'driver_availability_patterns', ['driver_id'], unique=False)


def downgrade() -> None:
    # Drop driver_availability_patterns table
    op.drop_index(op.f('ix_driver_availability_patterns_driver_id'), table_name='driver_availability_patterns')
    op.drop_table('driver_availability_patterns')
    
    # Drop driver_schedules table
    op.drop_index(op.f('ix_driver_schedules_driver_date'), table_name='driver_schedules')
    op.drop_index(op.f('ix_driver_schedules_schedule_date'), table_name='driver_schedules')
    op.drop_index(op.f('ix_driver_schedules_driver_id'), table_name='driver_schedules')
    op.drop_table('driver_schedules')