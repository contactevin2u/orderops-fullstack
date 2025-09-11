"""Add lorry stock verification tables

Revision ID: 20250911_add_verification_tables
Revises: 897aabf412f3_merge_migration_heads
Create Date: 2025-09-11 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250911_add_verification_tables'
down_revision = '897aabf412f3_merge_migration_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Create lorry_stock_verifications table
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
    # Drop indexes
    op.drop_index('ix_lorry_stock_verifications_verification_date', table_name='lorry_stock_verifications')
    op.drop_index('ix_lorry_stock_verifications_lorry_id', table_name='lorry_stock_verifications')
    op.drop_index('ix_lorry_stock_verifications_driver_id', table_name='lorry_stock_verifications')
    op.drop_index('ix_lorry_stock_verifications_assignment_id', table_name='lorry_stock_verifications')
    
    # Drop table
    op.drop_table('lorry_stock_verifications')