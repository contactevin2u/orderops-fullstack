#!/usr/bin/env python3
"""
Migration script to sync existing admin-created drivers with Firebase authentication.
This script will update existing driver records to use Firebase UIDs when drivers authenticate.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.models import Driver

def sync_drivers_with_firebase():
    """
    Find drivers created without Firebase UID and prepare them for Firebase sync.
    This script identifies drivers that need Firebase UID assignment.
    """
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("Scanning for drivers without Firebase UID...")
        
        # Find drivers without Firebase UID
        drivers_without_firebase = db.query(Driver).filter(
            Driver.firebase_uid.is_(None)
        ).all()
        
        print(f"Found {len(drivers_without_firebase)} drivers without Firebase UID:")
        for driver in drivers_without_firebase:
            print(f"  - ID: {driver.id}, Name: {driver.name}, Phone: {driver.phone}")
        
        # Find potential duplicate drivers (same name)
        print("\nChecking for potential duplicates by name...")
        driver_names = {}
        all_drivers = db.query(Driver).all()
        
        for driver in all_drivers:
            name = driver.name
            if name:
                if name not in driver_names:
                    driver_names[name] = []
                driver_names[name].append(driver)
        
        duplicates = {name: drivers for name, drivers in driver_names.items() if len(drivers) > 1}
        
        if duplicates:
            print(f"WARNING: Found {len(duplicates)} drivers with duplicate names:")
            for name, drivers in duplicates.items():
                print(f"  - '{name}': {[(d.id, d.firebase_uid, d.phone) for d in drivers]}")
        
        print("\nRecommended actions:")
        print("1. When drivers authenticate via Firebase, the system will now:")
        print("   - First check for existing drivers by name")  
        print("   - Update the existing driver record with Firebase UID")
        print("   - Avoid creating duplicate records")
        print("\n2. For immediate fixes:")
        if duplicates:
            for name, drivers in duplicates.items():
                firebase_driver = next((d for d in drivers if d.firebase_uid), None)
                admin_driver = next((d for d in drivers if not d.firebase_uid), None)
                
                if firebase_driver and admin_driver:
                    print(f"   - Merge {name}: Keep ID {admin_driver.id} (has assignments), add Firebase UID from ID {firebase_driver.id}")
    
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_drivers_with_firebase()