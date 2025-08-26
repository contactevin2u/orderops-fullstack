from alembic import op
import sqlalchemy as sa

revision = '0009_add_driver_routes'
down_revision = '0008_add_user_and_audit'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'driver_routes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('route_date', sa.Date(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_driver_routes_driver_id', 'driver_routes', ['driver_id'])
    op.create_index('ix_driver_routes_route_date', 'driver_routes', ['route_date'])

    op.add_column('trips', sa.Column('route_id', sa.BigInteger(), nullable=True))
    op.create_index('ix_trips_route_id', 'trips', ['route_id'])
    op.create_index('ix_trips_route_status', 'trips', ['route_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_trips_route_status', table_name='trips')
    op.drop_index('ix_trips_route_id', table_name='trips')
    op.drop_column('trips', 'route_id')

    op.drop_index('ix_driver_routes_route_date', table_name='driver_routes')
    op.drop_index('ix_driver_routes_driver_id', table_name='driver_routes')
    op.drop_table('driver_routes')
