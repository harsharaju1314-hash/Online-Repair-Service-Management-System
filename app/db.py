"""Database access and initialization module."""

import sqlite3
import os
from flask import g, current_app
from werkzeug.security import generate_password_hash

def get_db():
    """Open a unique database connection per request."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraint support in SQLite
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize database tables using schema.sql."""
    if app:
        with app.app_context():
            _run_init_schema()
    else:
        _run_init_schema()

def _run_init_schema():
    db = get_db()
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()

def seed_db():
    """Seed initial lookup data and default demo accounts if empty."""
    db = get_db()
    
    # 1. Seed Service Categories
    existing_cat = db.execute("SELECT COUNT(*) as count FROM service_categories").fetchone()
    if existing_cat['count'] == 0:
        categories = [
            ("Appliance Repair", "Kitchen and home electrical appliances such as refrigerators, ovens, microwaves, and washers."),
            ("Electrical Repair", "Circuit breakers, indoor/outdoor wiring, switches, lighting fixtures, and power outlets."),
            ("Plumbing", "Pipe leakages, drain clogs, faucet replacements, water heaters, and toilet repairs."),
            ("AC Service", "Air conditioning cleaning, coolant recharging, thermostat repairs, and duct maintenance.")
        ]
        db.executemany(
            "INSERT INTO service_categories (name, description, is_active) VALUES (?, ?, 1)",
            categories
        )

    # 2. Seed Technicians
    existing_techs = db.execute("SELECT COUNT(*) as count FROM technicians").fetchone()
    if existing_techs['count'] == 0:
        technicians = [
            ("Alex Johnson", "alex.tech@repairhub.local", "555-0101", "Appliance Repair"),
            ("Brian Martinez", "brian.tech@repairhub.local", "555-0102", "Electrical Repair"),
            ("Carlos Ramirez", "carlos.tech@repairhub.local", "555-0103", "Plumbing"),
            ("David Kim", "david.tech@repairhub.local", "555-0104", "AC Service")
        ]
        db.executemany(
            "INSERT INTO technicians (name, email, phone, specialization, is_available) VALUES (?, ?, ?, ?, 1)",
            technicians
        )

    # 3. Seed Default Users (Admin, Staff, Customer)
    existing_users = db.execute("SELECT COUNT(*) as count FROM users").fetchone()
    if existing_users['count'] == 0:
        users = [
            ("admin", "admin@repairhub.local", generate_password_hash("admin123"), "admin"),
            ("staff1", "staff1@repairhub.local", generate_password_hash("staff123"), "staff"),
            ("customer1", "customer1@repairhub.local", generate_password_hash("customer123"), "customer")
        ]
        db.executemany(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            users
        )

    db.commit()

def query_db(query, args=(), one=False):
    """Execute a read query and return row objects."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Execute an INSERT/UPDATE/DELETE query with parameters."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    lastrowid = cur.lastrowid
    rowcount = cur.rowcount
    cur.close()
    return {"lastrowid": lastrowid, "rowcount": rowcount}
