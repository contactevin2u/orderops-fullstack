from alembic import op
import sqlalchemy as sa

revision = '0005_add_payment_export_fields'
down_revision = '0004_add_parent_and_idempotent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('export_run_id', sa.String(length=40), nullable=True))
    op.add_column('payments', sa.Column('exported_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payments', sa.Column('idempotency_key', sa.String(length=64), nullable=True))
    op.create_index('ix_payments_idempotency_key', 'payments', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_payments_idempotency_key', table_name='payments')
    op.drop_column('payments', 'idempotency_key')
    op.drop_column('payments', 'exported_at')
    op.drop_column('payments', 'export_run_id')
