"""enhance_uid_system_with_extended_features

Revision ID: c4f8e2a91b12
Revises: 5852c5f76a34
Create Date: 2024-09-06 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0014_enhance_uid_system'
down_revision = '0013_add_uid_inventory_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to item table
    op.add_column('item', sa.Column('item_type', sa.Enum('NEW', 'RENTAL', name='itemtype'), nullable=False, server_default='RENTAL'))
    op.add_column('item', sa.Column('copy_number', sa.Integer(), nullable=True))
    op.add_column('item', sa.Column('current_driver_id', sa.Integer(), nullable=True))
    
    # Update item status enum to include new values
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'WITH_DRIVER'")
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'DELIVERED'") 
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'RETURNED'")
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'IN_REPAIR'")
    
    # Update item table to use new enum values
    op.execute("UPDATE item SET status = 'WAREHOUSE' WHERE status = 'ACTIVE'")
    
    # Add foreign key constraint for current_driver_id
    op.create_foreign_key('fk_item_current_driver_id', 'item', 'drivers', ['current_driver_id'], ['id'])
    
    # Update order_item_uid table to support new actions
    op.add_column('order_item_uid', sa.Column('sku_id', sa.Integer(), nullable=True))
    op.add_column('order_item_uid', sa.Column('sku_name', sa.String(), nullable=True))
    op.add_column('order_item_uid', sa.Column('notes', sa.Text(), nullable=True))
    
    # Add foreign key for sku_id
    op.create_foreign_key('fk_order_item_uid_sku_id', 'order_item_uid', 'sku', ['sku_id'], ['id'])
    
    # Drop the old unique constraint if it exists
    try:
        op.drop_constraint('uq_order_item_uid_order_uid_action', 'order_item_uid', type_='unique')
    except:
        pass
    
    # Drop the old check constraint if it exists
    try:
        op.drop_constraint('ck_order_item_uid_action', 'order_item_uid', type_='check')
    except:
        pass
    
    # Create new enum type for UID actions
    uidaction = postgresql.ENUM('LOAD_OUT', 'DELIVER', 'RETURN', 'REPAIR', 'SWAP', 'LOAD_IN', 'ISSUE', name='uidaction')
    uidaction.create(op.get_bind())
    
    # Convert action column to use new enum
    op.execute("ALTER TABLE order_item_uid ALTER COLUMN action TYPE uidaction USING action::text::uidaction")
    
    # Update sku_alias table structure
    op.add_column('sku_alias', sa.Column('alias', sa.String(), nullable=True))
    
    # Copy data from alias_text to alias if needed
    op.execute("UPDATE sku_alias SET alias = alias_text WHERE alias IS NULL")
    
    # Make alias column not null
    op.alter_column('sku_alias', 'alias', nullable=False)
    
    # Drop old alias_text column
    try:
        op.drop_column('sku_alias', 'alias_text')
    except:
        pass


def downgrade():
    # Reverse the changes
    op.drop_constraint('fk_item_current_driver_id', 'item', type_='foreignkey')
    op.drop_constraint('fk_order_item_uid_sku_id', 'order_item_uid', type_='foreignkey')
    
    op.drop_column('item', 'current_driver_id')
    op.drop_column('item', 'copy_number') 
    op.drop_column('item', 'item_type')
    
    op.drop_column('order_item_uid', 'notes')
    op.drop_column('order_item_uid', 'sku_name')
    op.drop_column('order_item_uid', 'sku_id')
    
    # Convert action back to string
    op.execute("ALTER TABLE order_item_uid ALTER COLUMN action TYPE varchar USING action::text")
    
    # Drop the new enum
    op.execute("DROP TYPE IF EXISTS uidaction")
    
    # Restore old constraints
    op.create_check_constraint('ck_order_item_uid_action', 'order_item_uid', "action IN ('ISSUE', 'RETURN')")
    op.create_unique_constraint('uq_order_item_uid_order_uid_action', 'order_item_uid', ['order_id', 'uid', 'action'])
    
    # Restore item status
    op.execute("UPDATE item SET status = 'ACTIVE' WHERE status = 'WAREHOUSE'")
    
    # Restore sku_alias structure
    op.add_column('sku_alias', sa.Column('alias_text', sa.String(), nullable=True))
    op.execute("UPDATE sku_alias SET alias_text = alias WHERE alias_text IS NULL")
    op.alter_column('sku_alias', 'alias_text', nullable=False)
    op.drop_column('sku_alias', 'alias')