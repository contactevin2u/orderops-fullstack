from alembic import op
import sqlalchemy as sa

revision = "0010_update_driver_device_fields"
down_revision = "0009_add_driver_routes"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # new fields
    op.add_column("driver_devices", sa.Column("app_version", sa.String(length=20), nullable=True))
    op.add_column("driver_devices", sa.Column("model", sa.String(length=100), nullable=True))
    op.add_column(
        "driver_devices",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "driver_devices",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ✅ add token first (nullable), backfill from fcm_token
    op.add_column("driver_devices", sa.Column("token", sa.String(length=255), nullable=True))
    op.execute("UPDATE driver_devices SET token = fcm_token WHERE token IS NULL")

    # make it NOT NULL after backfill
    op.alter_column("driver_devices", "token", nullable=False)

    # unique index on token to match the model
    op.create_index("ix_driver_devices_token", "driver_devices", ["token"], unique=True)

    # remove legacy column/index
    op.drop_index("ix_driver_devices_fcm_token", table_name="driver_devices")
    op.drop_column("driver_devices", "fcm_token")
    op.drop_column("driver_devices", "last_seen_at")

def downgrade() -> None:
    op.drop_index("ix_driver_devices_token", table_name="driver_devices")
    op.drop_column("driver_devices", "token")
    op.add_column("driver_devices", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("driver_devices", sa.Column("fcm_token", sa.String(length=255), nullable=False))
    op.create_index("ix_driver_devices_fcm_token", "driver_devices", ["fcm_token"])

    op.drop_column("driver_devices", "updated_at")
    op.drop_column("driver_devices", "created_at")
    op.drop_column("driver_devices", "model")
    op.drop_column("driver_devices", "app_version")
