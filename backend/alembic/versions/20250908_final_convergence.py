"""Final convergence: merge all actual heads

Revision ID: 20250908_final_convergence
Revises: 20250908_add_priority_lorry_id, drv_base_wh, add_background_jobs_table
Create Date: 2025-09-08 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250908_final_convergence'
down_revision = ('20250908_add_priority_lorry_id', 'drv_base_wh', 'bg_jobs_001')
branch_labels = None
depends_on = None


def upgrade():
    # Merge all heads - no operations needed
    # The priority_lorry_id column is added by 20250908_add_priority_lorry_id
    pass


def downgrade():
    # Merge migration - no operations to reverse
    pass