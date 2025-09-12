
#!/usr/bin/env python


"""add_missing_sku_table_columns

Revision ID: 2e273258bc37
Revises: d52784f990e2
Create Date: 2025-09-12 17:42:31.228487

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2e273258bc37'
down_revision = 'd52784f990e2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if sku table exists and what columns it has
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('sku'):
        columns = [col['name'] for col in inspector.get_columns('sku')]
        print(f"Current sku columns: {columns}")
        
        # Add missing SKU columns
        missing_columns = []
        
        if 'code' not in columns:
            # Add code column - this is critical for SKU identification
            op.add_column('sku', 
                sa.Column('code', sa.String(100), nullable=True)  # Initially nullable to add data
            )
            missing_columns.append('code')
        
        if 'name' not in columns:
            op.add_column('sku', 
                sa.Column('name', sa.String(200), nullable=False, server_default=sa.text("'Unknown SKU'"))
            )
            missing_columns.append('name')
            
        if 'category' not in columns:
            op.add_column('sku',
                sa.Column('category', sa.String(50), nullable=True)
            )
            missing_columns.append('category')
            
        if 'description' not in columns:
            op.add_column('sku',
                sa.Column('description', sa.Text(), nullable=True)
            )
            missing_columns.append('description')
            
        if 'is_serialized' not in columns:
            op.add_column('sku',
                sa.Column('is_serialized', sa.Boolean(), nullable=False, server_default=sa.text('false'))
            )
            missing_columns.append('is_serialized')
            
        if 'is_active' not in columns:
            op.add_column('sku',
                sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'))
            )
            missing_columns.append('is_active')
            
        if 'created_at' not in columns:
            op.add_column('sku',
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
            )
            missing_columns.append('created_at')
            
        if 'updated_at' not in columns:
            op.add_column('sku',
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
            )
            missing_columns.append('updated_at')
        
        # If we added the code column, populate it with sequential values
        if 'code' in missing_columns:
            # Update existing rows with sequential codes
            op.execute("UPDATE sku SET code = 'SKU' || LPAD(id::text, 6, '0') WHERE code IS NULL")
            # Make code column not nullable and unique after populating data
            op.alter_column('sku', 'code', nullable=False)
            op.create_unique_constraint('uq_sku_code', 'sku', ['code'])
        
        if missing_columns:
            print(f"✅ Added missing columns to sku: {missing_columns}")
        else:
            print("✅ sku table already has all required columns")
    else:
        print("⚠️ sku table doesn't exist - this shouldn't happen")

def downgrade() -> None:
    # Remove the added columns
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if inspector.has_table('sku'):
        columns = [col['name'] for col in inspector.get_columns('sku')]
        
        # Remove all columns we added
        columns_to_remove = [
            'updated_at', 'created_at', 'is_active', 'is_serialized', 
            'description', 'category', 'name', 'code'
        ]
        
        # Drop unique constraint first if it exists
        try:
            op.drop_constraint('uq_sku_code', 'sku', type_='unique')
        except:
            pass  # Constraint might not exist
        
        for column in columns_to_remove:
            if column in columns:
                op.drop_column('sku', column)
                
        print("✅ Removed all added columns from sku")
