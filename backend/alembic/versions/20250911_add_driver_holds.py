"""Add driver holds table for variance accountability

Revision ID: 20250911_add_driver_holds
Revises: 20250910_create_stock_transactions
Create Date: 2025-09-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250911_add_driver_holds'
down_revision = '20250911_add_verification_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Ghost revision - doing nothing (base tables don't exist yet)
    print("👻 Ghost driver holds migration - doing nothing")
    return

def upgrade_original():
    # Check if table exists before creating it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Create driver_holds table - only if it doesn't exist
    if not inspector.has_table('driver_holds'):
        op.create_table('driver_holds',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('related_assignment_id', sa.Integer(), nullable=True),
        sa.Column('related_verification_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['related_assignment_id'], ['lorry_assignments.id'], ),
        sa.ForeignKeyConstraint(['related_verification_id'], ['lorry_stock_verifications.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for performance
        op.create_index('ix_driver_holds_driver_id', 'driver_holds', ['driver_id'])
        op.create_index('ix_driver_holds_status', 'driver_holds', ['status'])
        op.create_index('ix_driver_holds_created_at', 'driver_holds', ['created_at'])
    

def downgrade():
    # Check if table exists before dropping it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Drop driver_holds table - only if it exists
    if inspector.has_table('driver_holds'):
        try:
            # Drop indexes
            op.drop_index('ix_driver_holds_created_at', table_name='driver_holds')
            op.drop_index('ix_driver_holds_status', table_name='driver_holds')
            op.drop_index('ix_driver_holds_driver_id', table_name='driver_holds')
        except Exception:
            pass  # Indexes might not exist
            
        # Drop table
        op.drop_table('driver_holds')