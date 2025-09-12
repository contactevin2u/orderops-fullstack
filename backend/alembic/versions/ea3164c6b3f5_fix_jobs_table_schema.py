
#!/usr/bin/env python


"""fix_jobs_table_schema

Revision ID: ea3164c6b3f5
Revises: 98460d749176
Create Date: 2025-09-12 10:18:07.664390

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ea3164c6b3f5'
down_revision = '98460d749176'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if jobs table exists
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'jobs'"))
    if result.fetchone():
        
        # Add last_error column if it doesn't exist (required by Job model)
        last_error_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'last_error'
        """)).fetchone()
        
        if not last_error_exists:
            op.add_column('jobs', sa.Column('last_error', sa.Text(), nullable=True))
            print("✅ Added last_error column to jobs table")
        else:
            print("✅ last_error column already exists")
            
        # Remove columns that are in migration but not in model (optional cleanup)
        # These columns were added by mistake in the original migration
        extra_columns_to_remove = ['max_attempts', 'started_at', 'completed_at', 'error_message']
        
        for col_name in extra_columns_to_remove:
            col_exists = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'jobs' AND column_name = '{col_name}'
            """)).fetchone()
            
            if col_exists:
                try:
                    op.drop_column('jobs', col_name)
                    print(f"✅ Removed unused {col_name} column")
                except Exception as e:
                    print(f"⚠️ Could not remove {col_name} column: {e}")
    else:
        print("⚠️ Jobs table doesn't exist - skipping schema fix")


def downgrade() -> None:
    connection = op.get_bind()
    
    # Check if jobs table exists
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'jobs'"))
    if result.fetchone():
        
        # Remove last_error column
        last_error_exists = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'last_error'
        """)).fetchone()
        
        if last_error_exists:
            op.drop_column('jobs', 'last_error')
            
        # Re-add the columns we removed (if needed for rollback)
        columns_to_readd = [
            ('max_attempts', sa.Integer(), 3),
            ('started_at', sa.DateTime(timezone=True), None),
            ('completed_at', sa.DateTime(timezone=True), None),
            ('error_message', sa.Text(), None)
        ]
        
        for col_name, col_type, default_val in columns_to_readd:
            try:
                if default_val is not None:
                    op.add_column('jobs', sa.Column(col_name, col_type, nullable=False, server_default=str(default_val)))
                else:
                    op.add_column('jobs', sa.Column(col_name, col_type, nullable=True))
            except Exception as e:
                print(f"Could not re-add {col_name}: {e}")
