"""add multiple pod photos support

Revision ID: 0008
Revises: 0007
Create Date: 2025-08-30 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for multiple PoD photos
    op.add_column('trips', sa.Column('pod_photo_url_1', sa.Text(), nullable=True))
    op.add_column('trips', sa.Column('pod_photo_url_2', sa.Text(), nullable=True))
    op.add_column('trips', sa.Column('pod_photo_url_3', sa.Text(), nullable=True))
    
    # Migrate existing data from pod_photo_url to pod_photo_url_1
    op.execute("""
        UPDATE trips 
        SET pod_photo_url_1 = pod_photo_url 
        WHERE pod_photo_url IS NOT NULL AND pod_photo_url != ''
    """)


def downgrade():
    # Migrate data back to single column
    op.execute("""
        UPDATE trips 
        SET pod_photo_url = pod_photo_url_1 
        WHERE pod_photo_url_1 IS NOT NULL
    """)
    
    # Drop the new columns
    op.drop_column('trips', 'pod_photo_url_3')
    op.drop_column('trips', 'pod_photo_url_2')
    op.drop_column('trips', 'pod_photo_url_1')