#!/usr/bin/env python3
"""
Create admin user after database reset
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User
from app.auth.password import hash_password
from app.core.config import settings

def create_admin_user():
    """Create default admin user"""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if admin already exists
        existing_admin = session.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("❌ Admin user already exists")
            return
        
        # Create admin user
        admin_user = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            role="ADMIN",
            is_active=True
        )
        session.add(admin_user)
        session.commit()
        print("✅ Admin user created successfully!")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Role: ADMIN")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_admin_user()