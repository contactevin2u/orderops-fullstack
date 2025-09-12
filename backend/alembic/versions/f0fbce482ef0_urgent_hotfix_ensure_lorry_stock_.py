
#!/usr/bin/env python


"""urgent_hotfix_ensure_lorry_stock_transactions_table

Revision ID: f0fbce482ef0
Revises: d34b5f823e8a
Create Date: 2025-09-12 20:30:38.463199

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f0fbce482ef0'
down_revision = 'd34b5f823e8a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ensure lorry_stock_transactions table exists with proper schema
    connection = op.get_bind()
    
    try:
        print("🚨 URGENT: Ensuring lorry_stock_transactions table exists...")
        
        # Check if table exists
        result = connection.execute(sa.text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'lorry_stock_transactions'
        """))
        
        if result.fetchone() is None:
            print("⚠️ lorry_stock_transactions table missing - creating now...")
            
            # Create the table with full schema
            connection.execute(sa.text("""
                CREATE TABLE lorry_stock_transactions (
                    id BIGSERIAL PRIMARY KEY,
                    lorry_id VARCHAR(50) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    uid VARCHAR(100) NOT NULL,
                    sku_id INTEGER,
                    order_id INTEGER REFERENCES orders(id),
                    driver_id INTEGER REFERENCES drivers(id),
                    admin_user_id INTEGER NOT NULL REFERENCES users(id),
                    notes TEXT,
                    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            
            # Create indexes
            connection.execute(sa.text("CREATE INDEX ix_lorry_stock_transactions_lorry_id ON lorry_stock_transactions(lorry_id)"))
            connection.execute(sa.text("CREATE INDEX ix_lorry_stock_transactions_uid ON lorry_stock_transactions(uid)"))
            connection.execute(sa.text("CREATE INDEX ix_lorry_stock_transactions_sku_id ON lorry_stock_transactions(sku_id)"))
            connection.execute(sa.text("CREATE INDEX ix_lorry_stock_transactions_order_id ON lorry_stock_transactions(order_id)"))
            connection.execute(sa.text("CREATE INDEX ix_lorry_stock_transactions_driver_id ON lorry_stock_transactions(driver_id)"))
            connection.execute(sa.text("CREATE INDEX ix_lorry_stock_transactions_transaction_date ON lorry_stock_transactions(transaction_date)"))
            
            print("✅ Created lorry_stock_transactions table with indexes")
        else:
            print("✅ lorry_stock_transactions table already exists")
            
            # Check for missing columns and add them if needed
            required_columns = [
                ('lorry_id', 'VARCHAR(50) NOT NULL'),
                ('action', 'VARCHAR(20) NOT NULL'),
                ('uid', 'VARCHAR(100) NOT NULL'),
                ('sku_id', 'INTEGER'),
                ('order_id', 'INTEGER REFERENCES orders(id)'),
                ('driver_id', 'INTEGER REFERENCES drivers(id)'),
                ('admin_user_id', 'INTEGER NOT NULL REFERENCES users(id)'),
                ('notes', 'TEXT'),
                ('transaction_date', 'TIMESTAMP WITH TIME ZONE NOT NULL'),
                ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL')
            ]
            
            for col_name, col_def in required_columns:
                result = connection.execute(sa.text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'lorry_stock_transactions' AND column_name = '{col_name}'
                """))
                
                if result.fetchone() is None:
                    connection.execute(sa.text(f"""
                        ALTER TABLE lorry_stock_transactions ADD COLUMN {col_name} {col_def}
                    """))
                    print(f"✅ Added missing column {col_name}")
        
        connection.commit()
        print("✅ lorry_stock_transactions table verification completed successfully")
        
    except Exception as e:
        print(f"⚠️ Table verification error: {e}")
        connection.rollback()
        raise

def downgrade() -> None:
    # Drop the table if created by this migration
    connection = op.get_bind()
    
    try:
        connection.execute(sa.text("DROP TABLE IF EXISTS lorry_stock_transactions CASCADE"))
        connection.commit()
        print("✅ Downgrade completed")
        
    except Exception as e:
        print(f"⚠️ Downgrade error: {e}")
        connection.rollback()
