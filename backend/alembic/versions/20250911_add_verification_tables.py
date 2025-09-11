"""Add lorry assignments and stock verification tables

Revision ID: 20250911_add_verification_tables
Revises: 20250910_stock_transactions
Create Date: 2025-09-11 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250911_add_verification_tables'
down_revision = '20250910_stock_transactions'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - doing nothing (base tables don't exist yet)
    print("👻 Ghost verification tables migration - doing nothing")
    return

def upgrade_original():
    # Check if tables exist before creating them
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Create lorry_assignments table first (required for foreign keys) - only if it doesn't exist
    if not inspector.has_table('lorry_assignments'):
        op.create_table('lorry_assignments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('stock_verified', sa.Boolean(), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for lorry_assignments
        op.create_index('ix_lorry_assignments_driver_id', 'lorry_assignments', ['driver_id'])
        op.create_index('ix_lorry_assignments_lorry_id', 'lorry_assignments', ['lorry_id'])
        op.create_index('ix_lorry_assignments_assignment_date', 'lorry_assignments', ['assignment_date'])
        op.create_index('ix_lorry_assignments_status', 'lorry_assignments', ['status'])
    
    # Create lorry_stock_verifications table - only if it doesn't exist
    if not inspector.has_table('lorry_stock_verifications'):
        op.create_table('lorry_stock_verifications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('verification_date', sa.Date(), nullable=False),
        sa.Column('scanned_uids', sa.Text(), nullable=False),
        sa.Column('total_scanned', sa.Integer(), nullable=False),
        sa.Column('expected_uids', sa.Text(), nullable=True),
        sa.Column('total_expected', sa.Integer(), nullable=True),
        sa.Column('variance_count', sa.Integer(), nullable=True),
        sa.Column('missing_uids', sa.Text(), nullable=True),
        sa.Column('unexpected_uids', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['lorry_assignments.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for performance
        op.create_index('ix_lorry_stock_verifications_assignment_id', 'lorry_stock_verifications', ['assignment_id'])
        op.create_index('ix_lorry_stock_verifications_driver_id', 'lorry_stock_verifications', ['driver_id'])
        op.create_index('ix_lorry_stock_verifications_lorry_id', 'lorry_stock_verifications', ['lorry_id'])
        op.create_index('ix_lorry_stock_verifications_verification_date', 'lorry_stock_verifications', ['verification_date'])


def downgrade():
    # Check if tables exist before dropping them
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Drop lorry_stock_verifications table indexes and table - only if it exists
    if inspector.has_table('lorry_stock_verifications'):
        try:
            op.drop_index('ix_lorry_stock_verifications_verification_date', table_name='lorry_stock_verifications')
            op.drop_index('ix_lorry_stock_verifications_lorry_id', table_name='lorry_stock_verifications')
            op.drop_index('ix_lorry_stock_verifications_driver_id', table_name='lorry_stock_verifications')
            op.drop_index('ix_lorry_stock_verifications_assignment_id', table_name='lorry_stock_verifications')
        except Exception:
            pass  # Indexes might not exist
        op.drop_table('lorry_stock_verifications')
    
    # Drop lorry_assignments table indexes and table - only if it exists
    if inspector.has_table('lorry_assignments'):
        try:
            op.drop_index('ix_lorry_assignments_status', table_name='lorry_assignments')
            op.drop_index('ix_lorry_assignments_assignment_date', table_name='lorry_assignments')
            op.drop_index('ix_lorry_assignments_lorry_id', table_name='lorry_assignments')
            op.drop_index('ix_lorry_assignments_driver_id', table_name='lorry_assignments')
        except Exception:
            pass  # Indexes might not exist
        op.drop_table('lorry_assignments')