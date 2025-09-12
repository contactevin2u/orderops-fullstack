
#!/usr/bin/env python


"""add_worker_jobs_table

Revision ID: 645250862483
Revises: 9e2616b970b7
Create Date: 2025-09-12 09:19:01.484665

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '645250862483'
down_revision = '9e2616b970b7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if the worker jobs table exists  
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'jobs'"))
    existing_jobs_table = result.fetchone()
    
    if existing_jobs_table:
        # Check if this is the old jobs table (has 'name' column) vs worker jobs table (has 'kind' column)
        name_column = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'name'
        """)).fetchone()
        
        kind_column = connection.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'kind'
        """)).fetchone()
        
        if name_column and not kind_column:
            # This is the old jobs table, rename it to avoid conflicts
            op.rename_table('jobs', 'job_definitions')
            print("✅ Renamed old 'jobs' table to 'job_definitions'")
            existing_jobs_table = None  # Now we need to create the worker jobs table
    
    if not existing_jobs_table:
        # Create worker jobs table with correct schema for the worker process
        op.create_table('jobs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('kind', sa.String(50), nullable=False),  # Job type: PARSE_CREATE, etc.
            sa.Column('status', sa.String(20), nullable=False, server_default='queued'),  # queued, running, completed, failed
            sa.Column('payload', sa.JSON(), nullable=True),  # Job parameters
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('result', sa.JSON(), nullable=True),
        )
        
        # Create indexes for worker performance
        op.create_index('ix_jobs_status', 'jobs', ['status'])
        op.create_index('ix_jobs_kind', 'jobs', ['kind'])
        op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
        op.create_index('ix_jobs_status_created', 'jobs', ['status', 'created_at'])
        
        print("✅ Created worker jobs table")
    else:
        print("✅ Worker jobs table already exists")
        
        # Ensure the table has all required columns
        required_columns = {
            'kind': sa.String(50),
            'status': sa.String(20), 
            'payload': sa.JSON(),
            'attempts': sa.Integer(),
            'max_attempts': sa.Integer(),
            'updated_at': sa.DateTime(timezone=True),
            'started_at': sa.DateTime(timezone=True),
            'completed_at': sa.DateTime(timezone=True),
            'error_message': sa.Text(),
            'result': sa.JSON()
        }
        
        for col_name, col_type in required_columns.items():
            col_exists = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'jobs' AND column_name = '{col_name}'
            """)).fetchone()
            
            if not col_exists:
                if col_name == 'kind':
                    op.add_column('jobs', sa.Column('kind', sa.String(50), nullable=False, server_default='UNKNOWN'))
                elif col_name == 'status':
                    op.add_column('jobs', sa.Column('status', sa.String(20), nullable=False, server_default='queued'))
                elif col_name == 'payload':
                    op.add_column('jobs', sa.Column('payload', sa.JSON(), nullable=True))
                elif col_name == 'attempts':
                    op.add_column('jobs', sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'))
                elif col_name == 'max_attempts':
                    op.add_column('jobs', sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'))
                elif col_name == 'updated_at':
                    op.add_column('jobs', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
                elif col_name == 'started_at':
                    op.add_column('jobs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
                elif col_name == 'completed_at':
                    op.add_column('jobs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
                elif col_name == 'error_message':
                    op.add_column('jobs', sa.Column('error_message', sa.Text(), nullable=True))
                elif col_name == 'result':
                    op.add_column('jobs', sa.Column('result', sa.JSON(), nullable=True))
                
                print(f"✅ Added missing column: {col_name}")
        
        # Ensure indexes exist
        try:
            op.create_index('ix_jobs_status', 'jobs', ['status'])
        except:
            pass
        try:
            op.create_index('ix_jobs_kind', 'jobs', ['kind']) 
        except:
            pass
        try:
            op.create_index('ix_jobs_status_created', 'jobs', ['status', 'created_at'])
        except:
            pass

def downgrade() -> None:
    connection = op.get_bind()
    
    # Check if jobs table exists  
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'jobs'"))
    
    if result.fetchone():
        # Drop indexes first
        indexes_to_drop = [
            'ix_jobs_status_created',
            'ix_jobs_created_at',
            'ix_jobs_kind',
            'ix_jobs_status'
        ]
        
        for index_name in indexes_to_drop:
            try:
                op.drop_index(index_name, 'jobs')
            except:
                pass  # Index might not exist
        
        # Drop the worker jobs table
        op.drop_table('jobs')
        
        print("✅ Dropped worker jobs table")
    
    # Check if job_definitions table exists (our renamed table)
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'job_definitions'"))
    
    if result.fetchone():
        # Rename job_definitions back to jobs
        op.rename_table('job_definitions', 'jobs')
        print("✅ Restored job_definitions table back to jobs")
