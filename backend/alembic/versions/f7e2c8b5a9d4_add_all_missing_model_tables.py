#!/usr/bin/env python

"""add_all_missing_model_tables

Revision ID: f7e2c8b5a9d4
Revises: b2f8e4a6d1c3
Create Date: 2025-09-12 11:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f7e2c8b5a9d4'
down_revision = 'b2f8e4a6d1c3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # Define all tables that should exist based on models
    required_tables = {
        'customers': {
            'columns': [
                ('id', sa.BigInteger(), {'autoincrement': True, 'nullable': False}),
                ('name', sa.String(200), {'nullable': False}),
                ('phone', sa.String(50), {'nullable': True}),
                ('address', sa.Text(), {'nullable': True}),
                ('map_url', sa.Text(), {'nullable': True}),
                ('created_at', sa.DateTime(timezone=True), {'server_default': sa.text('now()'), 'nullable': False}),
                ('updated_at', sa.DateTime(timezone=True), {'server_default': sa.text('now()'), 'nullable': False}),
            ],
            'primary_key': 'id',
            'indexes': ['phone']
        },
        'background_jobs': {
            'columns': [
                ('id', sa.String(36), {'nullable': False}),
                ('job_type', sa.String(50), {'nullable': False}),
                ('status', sa.String(20), {'nullable': False, 'server_default': "'pending'"}),
                ('input_data', sa.Text(), {'nullable': False}),
                ('result_data', sa.Text(), {'nullable': True}),
                ('error_message', sa.Text(), {'nullable': True}),
                ('progress', sa.Integer(), {'server_default': '0'}),
                ('progress_message', sa.String(200), {'nullable': True}),
                ('created_at', sa.DateTime(), {'server_default': sa.text('now()'), 'nullable': False}),
                ('started_at', sa.DateTime(), {'nullable': True}),
                ('completed_at', sa.DateTime(), {'nullable': True}),
                ('user_id', sa.Integer(), {'nullable': True}),
                ('session_id', sa.String(100), {'nullable': True}),
            ],
            'primary_key': 'id'
        },
        'organizations': {
            'columns': [
                ('id', sa.BigInteger(), {'autoincrement': True, 'nullable': False}),
                ('name', sa.String(200), {'nullable': False}),
                ('code', sa.String(50), {'nullable': True}),
                ('created_at', sa.DateTime(timezone=True), {'server_default': sa.text('now()'), 'nullable': False}),
                ('updated_at', sa.DateTime(timezone=True), {'server_default': sa.text('now()'), 'nullable': False}),
            ],
            'primary_key': 'id'
        },
        'performance_indexes': {
            'columns': [
                ('id', sa.BigInteger(), {'autoincrement': True, 'nullable': False}),
                ('driver_id', sa.BigInteger(), {'nullable': False}),
                ('date', sa.Date(), {'nullable': False}),
                ('deliveries', sa.Integer(), {'server_default': '0'}),
                ('collections', sa.Integer(), {'server_default': '0'}),
                ('performance_score', sa.Float(), {'server_default': '0.0'}),
                ('created_at', sa.DateTime(timezone=True), {'server_default': sa.text('now()'), 'nullable': False}),
            ],
            'primary_key': 'id'
        }
    }
    
    # Check and create missing tables
    for table_name, table_info in required_tables.items():
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"))
        if not result.fetchone():
            print(f"✅ Creating missing table: {table_name}")
            
            # Build columns for table creation
            columns = []
            for col_name, col_type, col_options in table_info['columns']:
                columns.append(sa.Column(col_name, col_type, **col_options))
            
            # Create table
            op.create_table(
                table_name,
                *columns,
                sa.PrimaryKeyConstraint(table_info['primary_key'])
            )
            
            # Create indexes if specified
            if 'indexes' in table_info:
                for index_col in table_info['indexes']:
                    op.create_index(f'ix_{table_name}_{index_col}', table_name, [index_col], unique=False)
                    
        else:
            print(f"✅ Table {table_name} already exists")
    
    # Also ensure all missing columns exist in existing tables
    missing_columns = {
        'orders': [
            ('parent_id', sa.BigInteger(), {'nullable': True}),
            ('penalty_fee', sa.Numeric(10, 2), {'server_default': '0'}),
            ('returned_at', sa.DateTime(timezone=True), {'nullable': True}),
            ('delivery_fee', sa.Numeric(10, 2), {'server_default': '0'}),
            ('discount', sa.Numeric(10, 2), {'server_default': '0'}),
            ('refund_amount', sa.Numeric(10, 2), {'server_default': '0'}),
            ('lorry_id', sa.BigInteger(), {'nullable': True}),
            ('priority', sa.Integer(), {'server_default': '0'}),
        ],
        'customers': [
            ('map_url', sa.Text(), {'nullable': True}),
        ]
    }
    
    for table_name, columns in missing_columns.items():
        # Check if table exists first
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"))
        if result.fetchone():
            for col_name, col_type, col_options in columns:
                # Check if column exists
                col_exists = connection.execute(sa.text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = '{col_name}'
                """)).fetchone()
                
                if not col_exists:
                    try:
                        op.add_column(table_name, sa.Column(col_name, col_type, **col_options))
                        print(f"✅ Added missing column {col_name} to {table_name}")
                    except Exception as e:
                        print(f"⚠️ Could not add column {col_name} to {table_name}: {e}")

def downgrade() -> None:
    # Only drop tables that we created in this migration
    connection = op.get_bind()
    
    tables_to_remove = ['organizations', 'performance_indexes']
    
    for table_name in tables_to_remove:
        result = connection.execute(sa.text(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"))
        if result.fetchone():
            op.drop_table(table_name)
            print(f"✅ Dropped table {table_name}")