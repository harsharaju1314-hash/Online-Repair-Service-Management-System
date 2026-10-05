-- Online Repair Service Management System - Database Schema (SQLite)
-- Enable Foreign Keys in SQLite connections: PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('customer', 'staff', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS technicians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    specialization TEXT NOT NULL,
    is_available INTEGER DEFAULT 1 CHECK (is_available IN (0, 1))
);

CREATE TABLE IF NOT EXISTS repair_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
    status TEXT NOT NULL DEFAULT 'REQUESTED' CHECK (status IN ('REQUESTED', 'ASSIGNED', 'SCHEDULED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'CANCELLED')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    preferred_date TEXT NOT NULL,
    preferred_time_slot TEXT NOT NULL,
    assigned_technician_id INTEGER,
    sla_target_hours INTEGER NOT NULL DEFAULT 24,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES service_categories(id),
    FOREIGN KEY (assigned_technician_id) REFERENCES technicians(id)
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    technician_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES repair_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES technicians(id)
);

CREATE TABLE IF NOT EXISTS request_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    user_id INTEGER,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES repair_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    user_id INTEGER,
    details TEXT NOT NULL,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for frequent query optimization
CREATE INDEX IF NOT EXISTS idx_requests_customer ON repair_requests(customer_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON repair_requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_priority ON repair_requests(priority);
CREATE INDEX IF NOT EXISTS idx_appointments_tech_date ON appointments(technician_id, appointment_date, time_slot);
CREATE INDEX IF NOT EXISTS idx_updates_request ON request_updates(request_id);
