
#!/usr/bin/env python


"""add_remaining_specialized_tables

Revision ID: cf2a82ca2c95
Revises: 3236997f2f3e
Create Date: 2025-09-11 21:33:58.729758

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cf2a82ca2c95'
down_revision = '3236997f2f3e'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create ALL remaining specialized tables for complete OrderOps functionality"""
    
    # ================================
    # INVENTORY & LORRY MANAGEMENT
    # ================================
    
    # Create lorries table
    op.create_table('lorries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('plate_number', sa.String(length=20), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lorry_id')
    )
    
    # Create lorry_assignments table
    op.create_table('lorry_assignments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=True),
        sa.Column('stock_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('stock_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='ASSIGNED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['shift_id'], ['driver_shifts.id']),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create lorry_stock table
    op.create_table('lorry_stock',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=0),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
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
        sa.ForeignKeyConstraint(['assignment_id'], ['lorry_assignments.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create lorry_stock_transactions table
    op.create_table('lorry_stock_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('uid', sa.String(length=100), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
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
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['related_assignment_id'], ['lorry_assignments.id']),
        sa.ForeignKeyConstraint(['related_verification_id'], ['lorry_stock_verifications.id']),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ================================
    # UID & ITEM TRACKING
    # ================================
    
    # Create uid_ledger table
    op.create_table('uid_ledger',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('scanned_at', sa.DateTime(), nullable=False),
        sa.Column('scanned_by_admin', sa.Integer(), nullable=True),
        sa.Column('scanned_by_driver', sa.Integer(), nullable=True),
        sa.Column('scanner_name', sa.String(length=100), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('sku_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('lorry_id', sa.String(length=50), nullable=True),
        sa.Column('location_notes', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('customer_name', sa.String(length=200), nullable=True),
        sa.Column('order_reference', sa.String(length=100), nullable=True),
        sa.Column('driver_scan_id', sa.String(length=100), nullable=True),
        sa.Column('sync_status', sa.String(length=20), nullable=False),
        sa.Column('recorded_by', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deletion_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
        sa.ForeignKeyConstraint(['scanned_by_admin'], ['users.id']),
        sa.ForeignKeyConstraint(['scanned_by_driver'], ['drivers.id']),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.ForeignKeyConstraint(['uid'], ['item.uid']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('driver_scan_id')
    )
    
    # Create order_item_uid table
    op.create_table('order_item_uid',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_item_id', sa.BigInteger(), nullable=False),
        sa.Column('uid', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('scanned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scanned_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id']),
        sa.ForeignKeyConstraint(['uid'], ['item.uid']),
        sa.ForeignKeyConstraint(['scanned_by'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ================================
    # AI & ANALYTICS
    # ================================
    
    # Create ai_verification_logs table
    op.create_table('ai_verification_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('trip_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('cash_collection_required', sa.Boolean(), nullable=True),
        sa.Column('analysis_result', sa.JSON(), nullable=True),
        sa.Column('verification_notes', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ================================
    # BUSINESS & OPERATIONS
    # ================================
    
    # Create upsell_records table
    op.create_table('upsell_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('upsell_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('driver_incentive', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='PENDING'),
        sa.Column('items_upsold', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create commissions table (different from commission_entries)
    op.create_table('commissions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ================================
    # DRIVER MANAGEMENT
    # ================================
    
    # Create driver_routes table
    op.create_table('driver_routes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create driver_schedules table
    op.create_table('driver_schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('schedule_date', sa.Date(), nullable=False),
        sa.Column('shift_type', sa.String(length=20), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create driver_availability_patterns table
    op.create_table('driver_availability_patterns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ================================
    # SUPPORT TABLES
    # ================================
    
    # Create sku_alias table
    op.create_table('sku_alias',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=False),
        sa.Column('alias', sa.String(length=200), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sku_id'], ['sku.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # ================================
    # PERFORMANCE INDEXES
    # ================================
    
    # Lorry management indexes
    op.create_index('ix_lorries_lorry_id', 'lorries', ['lorry_id'])
    op.create_index('ix_lorry_assignments_driver_id', 'lorry_assignments', ['driver_id'])
    op.create_index('ix_lorry_assignments_lorry_id', 'lorry_assignments', ['lorry_id'])
    op.create_index('ix_lorry_assignments_assignment_date', 'lorry_assignments', ['assignment_date'])
    op.create_index('ix_lorry_stock_lorry_id', 'lorry_stock', ['lorry_id'])
    op.create_index('ix_lorry_stock_date', 'lorry_stock', ['date'])
    op.create_index('ix_lorry_stock_verifications_assignment_id', 'lorry_stock_verifications', ['assignment_id'])
    op.create_index('ix_lorry_stock_transactions_lorry_id', 'lorry_stock_transactions', ['lorry_id'])
    op.create_index('ix_lorry_stock_transactions_uid', 'lorry_stock_transactions', ['uid'])
    op.create_index('ix_driver_holds_driver_id', 'driver_holds', ['driver_id'])
    op.create_index('ix_driver_holds_status', 'driver_holds', ['status'])
    
    # UID tracking indexes
    op.create_index('ix_uid_ledger_uid', 'uid_ledger', ['uid'])
    op.create_index('ix_uid_ledger_action', 'uid_ledger', ['action'])
    op.create_index('ix_uid_ledger_scanned_at', 'uid_ledger', ['scanned_at'])
    op.create_index('ix_order_item_uid_order_item_id', 'order_item_uid', ['order_item_id'])
    op.create_index('ix_order_item_uid_uid', 'order_item_uid', ['uid'])
    
    # AI verification indexes
    op.create_index('ix_ai_verification_logs_trip_id', 'ai_verification_logs', ['trip_id'])
    
    # Business operation indexes
    op.create_index('ix_upsell_records_order_id', 'upsell_records', ['order_id'])
    op.create_index('ix_upsell_records_driver_id', 'upsell_records', ['driver_id'])
    op.create_index('ix_upsell_records_status', 'upsell_records', ['status'])
    op.create_index('ix_commissions_trip_id', 'commissions', ['trip_id'])
    op.create_index('ix_commissions_driver_id', 'commissions', ['driver_id'])
    
    # Driver management indexes
    op.create_index('ix_driver_routes_driver_id', 'driver_routes', ['driver_id'])
    op.create_index('ix_driver_schedules_driver_id', 'driver_schedules', ['driver_id'])
    op.create_index('ix_driver_schedules_schedule_date', 'driver_schedules', ['schedule_date'])
    op.create_index('ix_driver_availability_patterns_driver_id', 'driver_availability_patterns', ['driver_id'])
    
    # Support table indexes
    op.create_index('ix_sku_alias_sku_id', 'sku_alias', ['sku_id'])
    op.create_index('ix_sku_alias_alias', 'sku_alias', ['alias'])
    op.create_index('ix_organizations_code', 'organizations', ['code'])
    
    print("✅ Created ALL remaining specialized tables: 17 tables with comprehensive indexes!")
    print("   📦 Lorry Management: lorries, lorry_assignments, lorry_stock, lorry_stock_verifications, lorry_stock_transactions, driver_holds")
    print("   🏷️  UID Tracking: uid_ledger, order_item_uid")
    print("   🤖 AI Analytics: ai_verification_logs")
    print("   💼 Business Operations: upsell_records, commissions, jobs")
    print("   👨‍💼 Driver Management: driver_routes, driver_schedules, driver_availability_patterns")
    print("   🛠️  Support: sku_alias, organizations")


def downgrade() -> None:
    """Drop all specialized tables"""
    # Drop in reverse dependency order
    op.drop_table('organizations')
    op.drop_table('sku_alias')
    op.drop_table('driver_availability_patterns')
    op.drop_table('driver_schedules')
    op.drop_table('driver_routes')
    op.drop_table('jobs')
    op.drop_table('commissions')
    op.drop_table('upsell_records')
    op.drop_table('ai_verification_logs')
    op.drop_table('order_item_uid')
    op.drop_table('uid_ledger')
    op.drop_table('driver_holds')
    op.drop_table('lorry_stock_transactions')
    op.drop_table('lorry_stock_verifications')
    op.drop_table('lorry_stock')
    op.drop_table('lorry_assignments')
    op.drop_table('lorries')
    print("✅ Dropped all specialized tables")
