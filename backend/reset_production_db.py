#!/usr/bin/env python3
"""
PRODUCTION DATABASE RESET SCRIPT
⚠️  WARNING: This will DELETE ALL DATA in production database ⚠️

This script will:
1. Drop all tables
2. Re-run all Alembic migrations from scratch
3. Create fresh admin user
4. Reset database to clean state

USE WITH EXTREME CAUTION - ALL DATA WILL BE LOST
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import User
from app.auth.password import hash_password
from app.core.config import settings

def confirm_reset():
    """Ask for confirmation before proceeding"""
    print("⚠️  DANGER: This will DELETE ALL DATA in production database")
    print(f"Database URL: {settings.DATABASE_URL[:50]}...")
    print("")
    print("This includes:")
    print("- All orders, trips, and deliveries")
    print("- All drivers and users")
    print("- All shifts and commissions")
    print("- All payments and invoices")
    print("- Everything will be permanently lost!")
    print("")
    
    confirm1 = input("Type 'DELETE_ALL_DATA' to confirm: ")
    if confirm1 != "DELETE_ALL_DATA":
        print("❌ Reset cancelled")
        sys.exit(1)
    
    confirm2 = input("Are you absolutely sure? Type 'YES_WIPE_PRODUCTION': ")
    if confirm2 != "YES_WIPE_PRODUCTION":
        print("❌ Reset cancelled")
        sys.exit(1)
    
    print("✅ Confirmation received. Starting database reset...")

def reset_database():
    """Reset the entire database"""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    print("🗑️  Dropping all tables...")
    
    # Drop all tables by dropping and recreating the schema
    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%' 
            AND tablename != 'information_schema'
        """))
        tables = [row[0] for row in result]
        
        # Drop alembic version table first
        if 'alembic_version' in tables:
            conn.execute(text("DROP TABLE alembic_version CASCADE"))
        
        # Drop all other tables
        for table in tables:
            if table != 'alembic_version':
                try:
                    conn.execute(text(f"DROP TABLE {table} CASCADE"))
                    print(f"  ✅ Dropped table: {table}")
                except Exception as e:
                    print(f"  ⚠️  Error dropping {table}: {e}")
        
        # Drop all custom types/enums
        result = conn.execute(text("""
            SELECT typname FROM pg_type 
            WHERE typtype = 'e' 
            AND typname NOT LIKE 'pg_%'
        """))
        enums = [row[0] for row in result]
        
        for enum_name in enums:
            try:
                conn.execute(text(f"DROP TYPE {enum_name} CASCADE"))
                print(f"  ✅ Dropped enum: {enum_name}")
            except Exception as e:
                print(f"  ⚠️  Error dropping enum {enum_name}: {e}")
        
        conn.commit()
    
    print("🔄 Running Alembic migrations from scratch...")
    
    # Run alembic upgrade head to recreate all tables
    os.system("cd backend && alembic upgrade head")
    
    print("👤 Creating default admin user...")
    
    # Create default admin user
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        admin_user = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            role="ADMIN",
            is_active=True
        )
        session.add(admin_user)
        session.commit()
        print("  ✅ Created admin user (username: admin, password: admin123)")
    except Exception as e:
        print(f"  ⚠️  Error creating admin user: {e}")
        session.rollback()
    finally:
        session.close()
    
    print("🎉 Database reset completed successfully!")
    print("")
    print("Next steps:")
    print("1. Login with username: admin, password: admin123")
    print("2. Create your production users and drivers")
    print("3. Configure the system for your needs")

if __name__ == "__main__":
    confirm_reset()
    reset_database()