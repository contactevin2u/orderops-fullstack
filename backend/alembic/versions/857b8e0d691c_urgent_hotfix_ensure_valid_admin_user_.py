
#!/usr/bin/env python


"""urgent_hotfix_ensure_valid_admin_user_for_transactions

Revision ID: 857b8e0d691c
Revises: f0fbce482ef0
Create Date: 2025-09-12 20:39:58.841437

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '857b8e0d691c'
down_revision = 'f0fbce482ef0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ensure there's a valid admin user for lorry stock transactions
    connection = op.get_bind()
    
    try:
        print("🚨 URGENT: Ensuring valid admin user exists for transactions...")
        
        # Check if there's at least one admin user
        result = connection.execute(sa.text("""
            SELECT id FROM users WHERE role = 'admin' LIMIT 1
        """))
        admin_user = result.fetchone()
        
        if not admin_user:
            print("⚠️ No admin user found - creating system admin...")
            
            # Create a system admin user
            connection.execute(sa.text("""
                INSERT INTO users (email, role, created_at) 
                VALUES ('system-admin@orderops.com', 'admin', NOW())
                ON CONFLICT (email) DO NOTHING
            """))
            print("✅ Created system admin user")
        else:
            print(f"✅ Found admin user with ID: {admin_user[0]}")
        
        # Check if Driver ID 2 (JIACHENG) exists as a user
        result = connection.execute(sa.text("""
            SELECT id FROM users WHERE id = 2
        """))
        user_2 = result.fetchone()
        
        if not user_2:
            print("⚠️ Driver ID 2 not found in users table - creating user record...")
            
            # Check if driver 2 exists in drivers table
            result = connection.execute(sa.text("""
                SELECT id, name FROM drivers WHERE id = 2
            """))
            driver_2 = result.fetchone()
            
            if driver_2:
                driver_name = driver_2[1] or "JIACHENG"
                connection.execute(sa.text("""
                    INSERT INTO users (id, email, role, created_at) 
                    VALUES (2, :email, 'driver', NOW())
                    ON CONFLICT (id) DO UPDATE SET 
                        email = EXCLUDED.email,
                        role = EXCLUDED.role
                """), {"email": f"{driver_name.lower()}@driver.local"})
                print(f"✅ Created user record for Driver {driver_name} (ID: 2)")
            else:
                print("⚠️ Driver ID 2 not found in drivers table either")
        else:
            print("✅ User ID 2 already exists")
        
        connection.commit()
        print("✅ Admin user verification completed successfully")
        
    except Exception as e:
        print(f"⚠️ Admin user verification error: {e}")
        connection.rollback()
        raise

def downgrade() -> None:
    pass
