#!/usr/bin/env python3
"""
Emergency migration fix: stamp current head and force single revision
"""
import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {cmd}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {cmd}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("🔥 EMERGENCY MIGRATION FIX: Stamping head")
    
    # Change to backend directory
    os.chdir('/opt/render/project/src/backend' if os.path.exists('/opt/render/project/src') else 'backend')
    
    # Step 1: Show current heads
    print("\n1️⃣ Checking current heads...")
    run_command("alembic heads")
    
    # Step 2: Stamp to our target revision
    print("\n2️⃣ Stamping to final convergence...")
    if run_command("alembic stamp 20250908_final_convergence"):
        print("✅ Successfully stamped database to single head")
        
        # Step 3: Verify we now have single head
        print("\n3️⃣ Verifying single head...")
        run_command("alembic heads")
        
        # Step 4: Run upgrade head (should work now)
        print("\n4️⃣ Running upgrade head...")
        if run_command("alembic upgrade head"):
            print("🎉 SUCCESS: Migration completed!")
        else:
            print("❌ Upgrade head failed even after stamp")
    else:
        print("❌ Failed to stamp database")

if __name__ == "__main__":
    main()