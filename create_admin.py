#!/usr/bin/env python3
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    print("Create Admin User")
    print("=" * 50)
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    role = input("Role (admin/manager) [admin]: ").lower() or 'admin'
    
    existing = User.query.filter_by(username=username).first()
    if existing:
        print(f"User '{username}' already exists!")
    else:
        user = User(username=username)
        user.set_password(password)
        
        if role == 'admin':
            user.is_admin = True
            user.is_manager = True  # Admins are also managers
            print(f"Creating ADMIN user with full access...")
        else:
            user.is_admin = False
            user.is_manager = True
            print(f"Creating MANAGER user with limited access...")
        
        db.session.add(user)
        db.session.commit()
        print(f"✅ User '{username}' created successfully as {role.upper()}!")