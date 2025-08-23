from alembic import op
import sqlalchemy as sa

revision = '0007_add_trip_commission_tables'
down_revision = '0006_add_driver_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trips',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ASSIGNED'),
        sa.Column('planned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('pod_photo_url', sa.Text(), nullable=True),
        sa.Column('payment_method', sa.String(length=30), nullable=True),
        sa.Column('payment_reference', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_trips_driver_status_planned', 'trips', ['driver_id', 'status', 'planned_at'])

    op.create_table(
        'trip_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('trip_id', sa.BigInteger(), sa.ForeignKey('trips.id'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('lat', sa.Numeric(10, 6), nullable=True),
        sa.Column('lng', sa.Numeric(10, 6), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'commissions',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('trip_id', sa.BigInteger(), sa.ForeignKey('trips.id'), nullable=False, unique=True),
        sa.Column('scheme', sa.String(length=20), nullable=False),
        sa.Column('rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('computed_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('actualized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actualization_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_commissions_actualized_at', 'commissions', ['actualized_at'])


def downgrade() -> None:
    op.drop_index('ix_commissions_actualized_at', table_name='commissions')
    op.drop_table('commissions')
    op.drop_table('trip_events')
    op.drop_index('ix_trips_driver_status_planned', table_name='trips')
    op.drop_table('trips')
