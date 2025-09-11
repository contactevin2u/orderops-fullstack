
#!/usr/bin/env python


"""add_background_jobs_table

Revision ID: 8cbeab73812a
Revises: 5dbd103021b7
Create Date: 2025-09-11 22:37:28.018344

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8cbeab73812a'
down_revision = '5dbd103021b7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add background_jobs table for job processing system"""
    
    # Check if table already exists
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'background_jobs'
        )
    """)).scalar()
    
    if not result:
        print("🔧 Creating background_jobs table...")
        
        op.create_table(
            'background_jobs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('job_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, default='pending'),
            sa.Column('input_data', sa.Text, nullable=False),
            sa.Column('result_data', sa.Text, nullable=True),
            sa.Column('error_message', sa.Text, nullable=True),
            sa.Column('progress', sa.Integer, default=0),
            sa.Column('progress_message', sa.String(200), nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column('started_at', sa.DateTime, nullable=True),
            sa.Column('completed_at', sa.DateTime, nullable=True),
            sa.Column('user_id', sa.Integer, nullable=True),
            sa.Column('session_id', sa.String(100), nullable=True),
        )
        
        # Create index on session_id for performance
        op.create_index('ix_background_jobs_session_id', 'background_jobs', ['session_id'])
        op.create_index('ix_background_jobs_created_at', 'background_jobs', ['created_at'])
        
        print("✅ Successfully created background_jobs table")
    else:
        print("✅ background_jobs table already exists - no action needed")

def downgrade() -> None:
    """Drop background_jobs table"""
    op.drop_table('background_jobs')
