#!/usr/bin/env python3
"""
Initialize Flask-Migrate for the application.
Run this script once to set up database migrations.

Usage:
    python init_migrations.py
"""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from flask_migrate import init, migrate, upgrade

def initialize_migrations():
    """Initialize Flask-Migrate and create initial migration."""
    print("Initializing Flask-Migrate...")
    
    # Create app instance
    app = create_app('development')
    
    with app.app_context():
        # Check if migrations directory already exists
        if os.path.exists('migrations'):
            print("Migrations directory already exists. Skipping initialization.")
        else:
            # Initialize Flask-Migrate
            init()
            print("✓ Migrations directory created")
        
        try:
            # Create initial migration from current models
            migrate(message='Initial migration from existing schema')
            print("✓ Initial migration created")
            
            # Apply the migration
            upgrade()
            print("✓ Migration applied to database")
            
            print("\n✓ Flask-Migrate initialization complete!")
            print("\nNext steps:")
            print("1. After making model changes, run: flask db migrate -m 'description'")
            print("2. Apply migrations with: flask db upgrade")
            print("3. Rollback with: flask db downgrade")
            
        except Exception as e:
            print(f"\n✗ Error during migration: {e}")
            print("\nIf the database already has tables, this is expected.")
            print("You can manually create a migration with:")
            print("  flask db revision --autogenerate -m 'Initial migration'")
            return False
    
    return True

if __name__ == '__main__':
    success = initialize_migrations()
    sys.exit(0 if success else 1)
