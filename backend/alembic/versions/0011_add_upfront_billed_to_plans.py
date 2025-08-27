from alembic import op
import sqlalchemy as sa

revision = '0011_add_upfront_billed_to_plans'
down_revision = '0010_update_driver_device_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('plans', sa.Column('upfront_billed_amount', sa.Numeric(12, 2), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('plans', 'upfront_billed_amount')
