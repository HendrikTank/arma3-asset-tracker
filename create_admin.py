#!/usr/bin/env python3
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            try:
                admin = User(username='admin', is_manager=True)
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✓ Admin user created successfully!")
                print("  Username: admin")
                print("  Password: admin123")
            except Exception as e:
                print(f"✗ Error creating admin user: {e}")
                print("Trying alternative method...")
                # Try direct hash insertion
                password_hash = generate_password_hash('admin123')
                try:
                    # Execute raw SQL to insert admin
                    from sqlalchemy import text
                    db.session.execute(
                        text("""
                            INSERT INTO users (username, password_hash, is_manager) 
                            VALUES (:username, :password_hash, :is_manager)
                        """),
                        {
                            'username': 'admin',
                            'password_hash': password_hash,
                            'is_manager': True
                        }
                    )
                    db.session.commit()
                    print("✓ Admin user created using direct SQL!")
                except Exception as e2:
                    print(f"✗ Alternative method also failed: {e2}")
                    db.session.rollback()
        else:
            print("⚠ Admin user already exists")
            # Update password if needed
            if input("Reset admin password? (y/n): ").lower() == 'y':
                admin.set_password('admin123')
                db.session.commit()
                print("✓ Admin password reset to 'admin123'")

if __name__ == '__main__':
    create_admin_user()