
#!/usr/bin/env python


"""create_commissions_table

Revision ID: cb9262d36f15
Revises: 8cbeab73812a
Create Date: 2025-09-12 07:59:05.484019

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cb9262d36f15'
down_revision = '8cbeab73812a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create commissions table
    op.create_table(
        'commissions',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('driver_id', sa.BigInteger(), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('trip_id', sa.BigInteger(), sa.ForeignKey('trips.id'), nullable=False),
        sa.Column('scheme', sa.String(20), nullable=False),
        sa.Column('rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('computed_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('actualized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actualization_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes
    op.create_index('ix_commissions_driver_id', 'commissions', ['driver_id'])
    op.create_index('ix_commissions_trip_id', 'commissions', ['trip_id'])
    op.create_index('ix_commissions_actualized_at', 'commissions', ['actualized_at'])

def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_commissions_actualized_at', 'commissions')
    op.drop_index('ix_commissions_trip_id', 'commissions')
    op.drop_index('ix_commissions_driver_id', 'commissions')
    
    # Drop table
    op.drop_table('commissions')
