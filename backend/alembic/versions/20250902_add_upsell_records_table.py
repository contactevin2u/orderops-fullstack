"""Add upsell_records table for tracking driver upsell incentives

Revision ID: 20250902_add_upsell_records_table
Revises: 20250831_add_driver_schedule_tables
Create Date: 2025-09-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250902_add_upsell_records_table'
down_revision = '20250831_add_driver_schedule_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'upsell_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('driver_id', sa.BigInteger(), nullable=False),
        sa.Column('trip_id', sa.BigInteger(), nullable=False),
        sa.Column('original_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('new_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('upsell_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('items_data', sa.Text(), nullable=False),
        sa.Column('upsell_notes', sa.Text(), nullable=True),
        sa.Column('driver_incentive', sa.Numeric(10, 2), nullable=False),
        sa.Column('incentive_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_upsell_records_order_id', 'order_id'),
        sa.Index('ix_upsell_records_driver_id', 'driver_id'),
        sa.Index('ix_upsell_records_released_at', 'released_at'),
    )


def downgrade() -> None:
    op.drop_table('upsell_records')