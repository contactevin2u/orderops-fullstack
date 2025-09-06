#!/usr/bin/env python3
"""
Migration runner for Render deployment
Handles database schema migrations safely in production
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

def run_migrations():
    """Run Alembic migrations safely"""
    try:
        # Import after path setup
        from alembic.config import Config
        from alembic import command
        
        # Set up Alembic config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("ERROR: DATABASE_URL environment variable not set")
            sys.exit(1)
            
        # Handle Render's postgres:// URLs
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
            
        # Add SSL mode for PostgreSQL if not present
        if database_url.startswith("postgresql") and "sslmode=" not in database_url:
            sep = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{sep}sslmode=require"
            
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Check current state
        print("Checking current migration state...")
        try:
            command.current(alembic_cfg)
        except Exception as e:
            print(f"Note: Could not check current state: {e}")
            
        # Run migrations
        print("Running migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully!")
        
        # Show final state
        print("Final migration state:")
        command.current(alembic_cfg)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()