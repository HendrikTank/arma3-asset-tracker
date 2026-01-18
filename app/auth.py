from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app import db, limiter
from app.models import User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limit login attempts
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and (user.is_manager or user.is_admin):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Route to appropriate dashboard based on role
            if user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.manager_dashboard'))
        else:
            flash('Invalid username or password, or insufficient permissions', 'error')
    
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))