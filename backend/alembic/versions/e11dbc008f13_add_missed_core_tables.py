
#!/usr/bin/env python


"""add_missed_core_tables

Revision ID: e11dbc008f13
Revises: cf2a82ca2c95
Create Date: 2025-09-11 21:41:39.357312

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e11dbc008f13'
down_revision = 'cf2a82ca2c95'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add the final missing core tables and fix users table"""
    
    # Get database connection to check table existence
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Fix users table - rename hashed_password to password_hash (only if needed)
    if inspector.has_table('users'):
        # Check if the column rename is needed
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'hashed_password' in columns and 'password_hash' not in columns:
            op.alter_column('users', 'hashed_password', new_column_name='password_hash')
            print("✅ Renamed users.hashed_password to users.password_hash")
        elif 'password_hash' in columns:
            print("✅ users.password_hash already exists - skipping rename")
    
    # Create audit_logs table for user action tracking (only if doesn't exist)
    if not inspector.has_table('audit_logs'):
        op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
        )
        print("✅ Created audit_logs table")
    else:
        print("✅ audit_logs table already exists - skipping")
    
    # Create idempotent_requests table for API request deduplication (only if doesn't exist)
    if not inspector.has_table('idempotent_requests'):
        op.create_table('idempotent_requests',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
        )
        print("✅ Created idempotent_requests table")
    else:
        print("✅ idempotent_requests table already exists - skipping")
    
    # Create plans table for rental/installment plans (only if doesn't exist)
    if not inspector.has_table('plans'):
        op.create_table('plans',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('plan_type', sa.String(length=20), nullable=False),  # RENTAL | INSTALLMENT
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('months', sa.Integer(), nullable=True),  # For installment
        sa.Column('monthly_amount', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('upfront_billed_amount', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('status', sa.String(length=20), nullable=False, default='ACTIVE'),  # ACTIVE|CANCELLED|COMPLETED
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
        )
        print("✅ Created plans table")
    else:
        print("✅ plans table already exists - skipping")
    
    # Create performance indexes (check if they exist first)
    existing_indexes = []
    try:
        for table in ['audit_logs', 'idempotent_requests', 'plans']:
            if inspector.has_table(table):
                existing_indexes.extend([idx['name'] for idx in inspector.get_indexes(table)])
    except:
        pass  # Ignore index check errors
    
    # Only create indexes that don't exist
    indexes_to_create = [
        ('ix_audit_logs_user_id', 'audit_logs', ['user_id']),
        ('ix_audit_logs_created_at', 'audit_logs', ['created_at']),
        ('ix_idempotent_requests_key', 'idempotent_requests', ['key']),
        ('ix_idempotent_requests_order_id', 'idempotent_requests', ['order_id']),
        ('ix_plans_order_id', 'plans', ['order_id']),
        ('ix_plans_status', 'plans', ['status'])
    ]
    
    for index_name, table_name, columns in indexes_to_create:
        if inspector.has_table(table_name) and index_name not in existing_indexes:
            try:
                op.create_index(index_name, table_name, columns)
                print(f"✅ Created index {index_name}")
            except:
                print(f"⚠️ Index {index_name} may already exist - skipping")
        elif index_name in existing_indexes:
            print(f"✅ Index {index_name} already exists - skipping")
    
    print("✅ Created final missing core tables:")
    print("   📋 audit_logs - User action tracking")
    print("   🔒 idempotent_requests - API request deduplication")
    print("   📅 plans - Rental/installment plan management")

def downgrade() -> None:
    """Drop the core tables"""
    op.drop_table('plans')
    op.drop_table('idempotent_requests')
    op.drop_table('audit_logs')
    print("✅ Dropped core tables")
