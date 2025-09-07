"""Add lorry assignment and stock verification models

Revision ID: 20250907_add_lorry_assignment_models
Revises: 3c8b1c03e2ca
Create Date: 2025-09-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250907_add_lorry_assignment_models'
down_revision = '3c8b1c03e2ca'
branch_labels = None
depends_on = None


def upgrade():
    # Create lorry_assignments table
    op.create_table('lorry_assignments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=True),
        sa.Column('stock_verified', sa.Boolean(), nullable=False),
        sa.Column('stock_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['shift_id'], ['driver_shifts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lorry_assignments_assignment_date'), 'lorry_assignments', ['assignment_date'], unique=False)
    op.create_index(op.f('ix_lorry_assignments_driver_id'), 'lorry_assignments', ['driver_id'], unique=False)
    op.create_index(op.f('ix_lorry_assignments_lorry_id'), 'lorry_assignments', ['lorry_id'], unique=False)
    op.create_index(op.f('ix_lorry_assignments_shift_id'), 'lorry_assignments', ['shift_id'], unique=False)

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
    op.create_index(op.f('ix_lorry_stock_verifications_assignment_id'), 'lorry_stock_verifications', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_lorry_stock_verifications_driver_id'), 'lorry_stock_verifications', ['driver_id'], unique=False)
    op.create_index(op.f('ix_lorry_stock_verifications_lorry_id'), 'lorry_stock_verifications', ['lorry_id'], unique=False)
    op.create_index(op.f('ix_lorry_stock_verifications_verification_date'), 'lorry_stock_verifications', ['verification_date'], unique=False)

    # Create driver_holds table
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
    op.create_index(op.f('ix_driver_holds_driver_id'), 'driver_holds', ['driver_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_driver_holds_driver_id'), table_name='driver_holds')
    op.drop_table('driver_holds')
    op.drop_index(op.f('ix_lorry_stock_verifications_verification_date'), table_name='lorry_stock_verifications')
    op.drop_index(op.f('ix_lorry_stock_verifications_lorry_id'), table_name='lorry_stock_verifications')
    op.drop_index(op.f('ix_lorry_stock_verifications_driver_id'), table_name='lorry_stock_verifications')
    op.drop_index(op.f('ix_lorry_stock_verifications_assignment_id'), table_name='lorry_stock_verifications')
    op.drop_table('lorry_stock_verifications')
    op.drop_index(op.f('ix_lorry_assignments_shift_id'), table_name='lorry_assignments')
    op.drop_index(op.f('ix_lorry_assignments_lorry_id'), table_name='lorry_assignments')
    op.drop_index(op.f('ix_lorry_assignments_driver_id'), table_name='lorry_assignments')
    op.drop_index(op.f('ix_lorry_assignments_assignment_date'), table_name='lorry_assignments')
    op.drop_table('lorry_assignments')