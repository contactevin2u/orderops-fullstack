
#!/usr/bin/env python


"""add_missing_worker_tables

Revision ID: 98460d749176
Revises: 645250862483
Create Date: 2025-09-12 09:31:05.512818

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '98460d749176'
down_revision = '645250862483'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Create plans table if it doesn't exist (critical for create_order_from_parsed)
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'plans'"))
    if not result.fetchone():
        op.create_table('plans',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
            sa.Column('plan_type', sa.String(20), nullable=False),  # RENTAL | INSTALLMENT
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('months', sa.Integer(), nullable=True),  # For installment
            sa.Column('monthly_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('upfront_billed_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),  # ACTIVE|CANCELLED|COMPLETED
        )
        op.create_index('ix_plans_order_id', 'plans', ['order_id'])
        op.create_index('ix_plans_plan_type', 'plans', ['plan_type'])
        print("✅ Created plans table")
    else:
        print("✅ Plans table already exists")
    
    # 2. Create driver_routes table if it doesn't exist (critical for AssignmentService)
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'driver_routes'"))
    if not result.fetchone():
        op.create_table('driver_routes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('route_id', sa.Integer(), sa.ForeignKey('routes.id'), nullable=False),
            sa.Column('assigned_date', sa.Date(), nullable=False),
            sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_driver_routes_driver_id', 'driver_routes', ['driver_id'])
        op.create_index('ix_driver_routes_route_id', 'driver_routes', ['route_id'])
        op.create_index('ix_driver_routes_status', 'driver_routes', ['status'])
        print("✅ Created driver_routes table")
    else:
        print("✅ Driver_routes table already exists")
    
    # 3. Create driver_shifts table if it doesn't exist (optional for AssignmentService)
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'driver_shifts'"))
    if not result.fetchone():
        op.create_table('driver_shifts',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('driver_id', sa.Integer(), sa.ForeignKey('drivers.id'), nullable=False),
            sa.Column('shift_date', sa.Date(), nullable=False),
            sa.Column('shift_type', sa.String(20), nullable=False, server_default='FULL_DAY'),  # MORNING, AFTERNOON, FULL_DAY
            sa.Column('start_time', sa.Time(), nullable=True),
            sa.Column('end_time', sa.Time(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='SCHEDULED'),  # SCHEDULED, ACTIVE, COMPLETED, CANCELLED
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_driver_shifts_driver_id', 'driver_shifts', ['driver_id'])
        op.create_index('ix_driver_shifts_shift_date', 'driver_shifts', ['shift_date'])
        op.create_index('ix_driver_shifts_status', 'driver_shifts', ['status'])
        print("✅ Created driver_shifts table")
    else:
        print("✅ Driver_shifts table already exists")
    
    # 4. Ensure routes table exists (referenced by driver_routes)
    result = connection.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name = 'routes'"))
    if not result.fetchone():
        op.create_table('routes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('area', sa.String(100), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_routes_name', 'routes', ['name'])
        op.create_index('ix_routes_is_active', 'routes', ['is_active'])
        op.create_index('ix_routes_priority', 'routes', ['priority'])
        print("✅ Created routes table")
    else:
        print("✅ Routes table already exists")


def downgrade() -> None:
    """Drop the worker-required tables"""
    connection = op.get_bind()
    
    # Drop in reverse order to handle foreign key constraints
    tables_to_drop = ['driver_shifts', 'driver_routes', 'plans', 'routes']
    
    for table in tables_to_drop:
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table}'"))
        if result.fetchone():
            try:
                op.drop_table(table)
                print(f"✅ Dropped {table} table")
            except Exception as e:
                print(f"⚠️  Could not drop {table}: {e}")
        else:
            print(f"✅ {table} table doesn't exist - skipping")
