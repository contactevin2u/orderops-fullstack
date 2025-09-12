#!/usr/bin/env python3
"""
Sync all Firebase users into the drivers table.
This ensures all drivers created in Firebase Console are available in the database.
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.models import Driver
from app.auth.firebase import list_all_firebase_users

def sync_firebase_drivers():
    """
    Fetch all Firebase users and create/update driver records in the database
    """
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("🔍 Fetching all users from Firebase Auth...")
        firebase_users = list_all_firebase_users()
        print(f"📋 Found {len(firebase_users)} Firebase users")
        
        synced_count = 0
        updated_count = 0
        
        for firebase_user in firebase_users:
            uid = firebase_user["uid"]
            name = firebase_user.get("display_name")
            phone = firebase_user.get("phone_number") 
            email = firebase_user.get("email")
            
            print(f"Processing: {name} ({uid})")
            
            # Check if driver already exists
            existing_driver = db.query(Driver).filter(Driver.firebase_uid == uid).first()
            
            if existing_driver:
                # Update existing driver with Firebase data
                updated = False
                if name and existing_driver.name != name:
                    existing_driver.name = name
                    updated = True
                if phone and existing_driver.phone != phone:
                    existing_driver.phone = phone
                    updated = True
                
                if updated:
                    print(f"  ✏️  Updated existing driver ID {existing_driver.id}")
                    updated_count += 1
                else:
                    print(f"  ✅ Driver ID {existing_driver.id} already up to date")
            else:
                # Create new driver from Firebase user
                new_driver = Driver(
                    firebase_uid=uid,
                    name=name,
                    phone=phone
                )
                db.add(new_driver)
                print(f"  ➕ Created new driver from Firebase user")
                synced_count += 1
        
        db.commit()
        print(f"\n🎉 Sync complete!")
        print(f"   📊 {synced_count} new drivers created")
        print(f"   📊 {updated_count} existing drivers updated")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_firebase_drivers()