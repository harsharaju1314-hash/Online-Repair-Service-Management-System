"""Authentication and session management module."""

import functools
import re
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import query_db, execute_db

auth_bp = Blueprint('auth', __name__)

def log_activity(event_type, details, user_id=None, ip_address=None):
    """Record an audit trail event in activity_logs."""
    try:
        if user_id is None and hasattr(g, 'user') and g.user:
            user_id = g.user['id']
        if ip_address is None and request:
            ip_address = request.remote_addr
        execute_db(
            "INSERT INTO activity_logs (event_type, user_id, details, ip_address) VALUES (?, ?, ?, ?)",
            (event_type, user_id, details, ip_address)
        )
    except Exception as e:
        current_app.logger.warning(f"Failed to log activity: {e}")

@auth_bp.before_app_request
def load_logged_in_user():
    """Load logged-in user from session into flask.g before every request."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        g.user_role = None
    else:
        g.user = query_db("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,), one=True)
        g.user_role = g.user['role'] if g.user else None

def login_required(view):
    """Decorator to require user authentication."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required"}), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

def role_required(allowed_roles):
    """Decorator to enforce role-based access control."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Authentication required"}), 401
                flash("Please log in first.", "warning")
                return redirect(url_for('auth.login'))
            
            roles = allowed_roles if isinstance(allowed_roles, (list, tuple, set)) else [allowed_roles]
            if g.user_role not in roles:
                current_app.logger.warning(
                    f"Forbidden access attempt: user={g.user['username']}, role={g.user_role}, path={request.path}"
                )
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Forbidden: insufficient role permissions"}), 403
                flash("Access denied: You do not have permission to view this resource.", "danger")
                return redirect(url_for('routes.dashboard'))
            return view(**kwargs)
        return wrapped_view
    return decorator

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new customer account."""
    if g.user:
        return redirect(url_for('routes.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        error = None

        if not username:
            error = "Username is required."
        elif len(username) < 3 or len(username) > 30:
            error = "Username must be between 3 and 30 characters."
        elif not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            error = "Username can only contain alphanumeric characters, underscores, dots, and hyphens."
        elif not email or '@' not in email:
            error = "A valid email address is required."
        elif not password or len(password) < 6:
            error = "Password must be at least 6 characters long."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif query_db("SELECT id FROM users WHERE username = ?", (username,), one=True) is not None:
            error = f"Username '{username}' is already taken."
        elif query_db("SELECT id FROM users WHERE email = ?", (email,), one=True) is not None:
            error = f"Email '{email}' is already registered."

        if error is None:
            pwd_hash = generate_password_hash(password)
            result = execute_db(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'customer')",
                (username, email, pwd_hash)
            )
            log_activity("USER_REGISTERED", f"New customer registered: {username}", user_id=result["lastrowid"])
            current_app.logger.info(f"Customer registered successfully: {username}")
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('auth.login'))

        flash(error, "danger")

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate user and initialize session."""
    if g.user:
        return redirect(url_for('routes.dashboard'))

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        error = None

        if not username_or_email or not password:
            error = "Both username/email and password are required."
        else:
            user = query_db(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (username_or_email, username_or_email.lower()),
                one=True
            )
            if user is None or not check_password_hash(user['password_hash'], password):
                error = "Invalid username/email or password."
                log_activity("LOGIN_FAILED", f"Failed login attempt for identifier: {username_or_email}")
                current_app.logger.warning(f"Failed login attempt for {username_or_email}")
            else:
                session.clear()
                session['user_id'] = user['id']
                log_activity("LOGIN_SUCCESS", f"User logged in: {user['username']}", user_id=user['id'])
                current_app.logger.info(f"User logged in: {user['username']} ({user['role']})")
                flash(f"Welcome back, {user['username']}!", "success")
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('routes.dashboard'))

        flash(error, "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Clear session and log out."""
    if g.user:
        log_activity("LOGOUT", f"User logged out: {g.user['username']}")
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('auth.login'))
