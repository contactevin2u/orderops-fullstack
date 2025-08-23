from alembic import op
import sqlalchemy as sa

revision = '0006_add_driver_tables'
down_revision = '0005_add_payment_export_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'drivers',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('firebase_uid', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_drivers_firebase_uid', 'drivers', ['firebase_uid'], unique=True)
    op.create_index('ix_drivers_phone', 'drivers', ['phone'], unique=False)

    op.create_table(
        'driver_devices',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('fcm_token', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_driver_devices_driver_id', 'driver_devices', ['driver_id'])
    op.create_index('ix_driver_devices_fcm_token', 'driver_devices', ['fcm_token'])


def downgrade() -> None:
    op.drop_index('ix_driver_devices_fcm_token', table_name='driver_devices')
    op.drop_index('ix_driver_devices_driver_id', table_name='driver_devices')
    op.drop_table('driver_devices')

    op.drop_index('ix_drivers_phone', table_name='drivers')
    op.drop_index('ix_drivers_firebase_uid', table_name='drivers')
    op.drop_table('drivers')
