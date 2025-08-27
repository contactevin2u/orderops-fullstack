from alembic import op
import sqlalchemy as sa

revision = "0010_update_driver_device_fields"
down_revision = "0009_add_driver_routes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New/modern fields (keep if already present in your draft)
    op.add_column("driver_devices", sa.Column("app_version", sa.String(length=20), nullable=True))
    op.add_column("driver_devices", sa.Column("model", sa.String(length=100), nullable=True))
    op.add_column("driver_devices", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("driver_devices", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    # Add token, backfill, and enforce NOT NULL
    op.add_column("driver_devices", sa.Column("token", sa.String(length=255), nullable=True))
    op.execute("UPDATE driver_devices SET token = fcm_token WHERE token IS NULL")
    op.alter_column("driver_devices", "token", nullable=False)

    # ---- BEGIN: de-dupe within (driver_id, token) ----
    # Optional backup for audit/recovery
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS driver_devices_dups_driver_token AS
        SELECT *
        FROM (
            SELECT d.*,
                   ROW_NUMBER() OVER (
                     PARTITION BY d.driver_id, d.token
                     ORDER BY d.updated_at DESC NULLS LAST,
                              d.created_at DESC NULLS LAST,
                              d.id DESC
                   ) AS rn
            FROM driver_devices d
            WHERE d.token IS NOT NULL
        ) x
        WHERE x.rn > 1;
    """
    )

    # Delete duplicates, keep the newest per (driver_id, token)
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                     PARTITION BY driver_id, token
                     ORDER BY updated_at DESC NULLS LAST,
                              created_at DESC NULLS LAST,
                              id DESC
                   ) AS rn
            FROM driver_devices
            WHERE token IS NOT NULL
        )
        DELETE FROM driver_devices d
        USING ranked r
        WHERE d.id = r.id
          AND r.rn > 1;
    """
    )
    # ---- END: de-dupe ----

    # Drop any prior single-column token index if it existed
    op.execute("DROP INDEX IF EXISTS ix_driver_devices_token")

    # Composite unique index (Option B)
    op.create_index(
        "uq_driver_devices_driver_id_token",
        "driver_devices",
        ["driver_id", "token"],
        unique=True,
    )

    # Remove legacy fields/index
    op.drop_index("ix_driver_devices_fcm_token", table_name="driver_devices")
    op.drop_column("driver_devices", "fcm_token")
    op.drop_column("driver_devices", "last_seen_at")


def downgrade() -> None:
    op.drop_index("uq_driver_devices_driver_id_token", table_name="driver_devices")
    op.add_column("driver_devices", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("driver_devices", sa.Column("fcm_token", sa.String(length=255), nullable=False))
    op.create_index("ix_driver_devices_fcm_token", "driver_devices", ["fcm_token"])
    op.drop_column("driver_devices", "token")
    op.drop_column("driver_devices", "updated_at")
    op.drop_column("driver_devices", "created_at")
    op.drop_column("driver_devices", "model")
    op.drop_column("driver_devices", "app_version")
