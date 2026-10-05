from datetime import datetime, timezone
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.security import generate_password_hash
from app.auth import login_required, role_required, log_activity
from app.db import query_db, execute_db
from app.sla import calculate_sla_status, SLA_TARGET_HOURS

routes_bp = Blueprint('routes', __name__)

VALID_STATUS_TRANSITIONS = {
    'REQUESTED': ['ASSIGNED', 'CANCELLED'],
    'ASSIGNED': ['SCHEDULED', 'IN_PROGRESS', 'CANCELLED'],
    'SCHEDULED': ['IN_PROGRESS', 'CANCELLED'],
    'IN_PROGRESS': ['RESOLVED', 'CANCELLED'],
    'RESOLVED': ['CLOSED', 'IN_PROGRESS'],  # Allow reopen to IN_PROGRESS if verification fails
    'CLOSED': [],                           # Terminal state
    'CANCELLED': []                         # Terminal state
}

@routes_bp.route('/')
def index():
    if g.user:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('auth.login'))

@routes_bp.route('/dashboard')
@login_required
def dashboard():
    """Render role-specific dashboard."""
    role = g.user_role
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if role == 'customer':
        # Fetch requests owned by this customer
        requests = query_db(
            """
            SELECT r.*, c.name as category_name, t.name as technician_name
            FROM repair_requests r
            JOIN service_categories c ON r.category_id = c.id
            LEFT JOIN technicians t ON r.assigned_technician_id = t.id
            WHERE r.customer_id = ?
            ORDER BY r.created_at DESC
            """,
            (g.user['id'],)
        )
        enriched_requests = []
        for req in requests:
            sla_info = calculate_sla_status(req['created_at'], req['priority'], req['resolved_at'], now)
            req_dict = dict(req)
            req_dict['sla'] = sla_info
            enriched_requests.append(req_dict)

        return render_template('customer/dashboard.html', requests=enriched_requests)

    elif role in ('staff', 'admin'):
        status_filter = request.args.get('status', '')
        priority_filter = request.args.get('priority', '')
        
        query = """
            SELECT r.*, c.name as category_name, t.name as technician_name, u.username as customer_username
            FROM repair_requests r
            JOIN service_categories c ON r.category_id = c.id
            JOIN users u ON r.customer_id = u.id
            LEFT JOIN technicians t ON r.assigned_technician_id = t.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND r.status = ?"
            params.append(status_filter)
        if priority_filter:
            query += " AND r.priority = ?"
            params.append(priority_filter)
        
        query += " ORDER BY CASE r.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, r.created_at ASC"
        
        all_requests = query_db(query, tuple(params))
        
        enriched_requests = []
        counts = {'total': 0, 'open': 0, 'breached': 0, 'approaching': 0, 'resolved': 0}
        
        for req in all_requests:
            sla_info = calculate_sla_status(req['created_at'], req['priority'], req['resolved_at'], now)
            req_dict = dict(req)
            req_dict['sla'] = sla_info
            enriched_requests.append(req_dict)
            
            counts['total'] += 1
            if req['status'] in ('REQUESTED', 'ASSIGNED', 'SCHEDULED', 'IN_PROGRESS'):
                counts['open'] += 1
                if sla_info['is_breached']:
                    counts['breached'] += 1
                elif sla_info['is_approaching']:
                    counts['approaching'] += 1
            elif req['status'] in ('RESOLVED', 'CLOSED'):
                counts['resolved'] += 1

        if role == 'admin':
            users_count = query_db("SELECT COUNT(*) as count FROM users", one=True)['count']
            techs_count = query_db("SELECT COUNT(*) as count FROM technicians", one=True)['count']
            return render_template(
                'admin/dashboard.html',
                requests=enriched_requests,
                counts=counts,
                users_count=users_count,
                techs_count=techs_count,
                status_filter=status_filter,
                priority_filter=priority_filter
            )
        else:
            return render_template(
                'staff/dashboard.html',
                requests=enriched_requests,
                counts=counts,
                status_filter=status_filter,
                priority_filter=priority_filter
            )

# ----------------- Customer Actions -----------------

@routes_bp.route('/requests/new', methods=['GET', 'POST'])
@login_required
@role_required(['customer', 'admin'])
def new_request():
    """Submit a new repair request."""
    categories = query_db("SELECT * FROM service_categories WHERE is_active = 1 ORDER BY name ASC")
    
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        preferred_date = request.form.get('preferred_date', '').strip()
        preferred_time_slot = request.form.get('preferred_time_slot', '').strip()
        
        error = None
        if not category_id:
            error = "Please select a repair category."
        elif not title or len(title) < 5:
            error = "Title must be at least 5 characters long."
        elif not description or len(description) < 10:
            error = "Description must provide at least 10 characters of detail."
        elif not preferred_date:
            error = "Please select a preferred service date."
        elif not preferred_time_slot:
            error = "Please select a preferred time slot."

        if error is None:
            priority = 'MEDIUM'
            sla_target = SLA_TARGET_HOURS.get(priority, 24)
            result = execute_db(
                """
                INSERT INTO repair_requests 
                (customer_id, category_id, priority, status, title, description, preferred_date, preferred_time_slot, sla_target_hours)
                VALUES (?, ?, ?, 'REQUESTED', ?, ?, ?, ?, ?)
                """,
                (g.user['id'], category_id, priority, title, description, preferred_date, preferred_time_slot, sla_target)
            )
            req_id = result['lastrowid']
            execute_db(
                "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, NULL, 'REQUESTED', 'Request created by customer')",
                (req_id, g.user['id'])
            )
            log_activity("REQUEST_CREATED", f"Repair request #{req_id} created: {title}", user_id=g.user['id'])
            flash(f"Repair request #{req_id} submitted successfully!", "success")
            return redirect(url_for('routes.view_request', request_id=req_id))

        flash(error, "danger")

    return render_template('customer/new_request.html', categories=categories)

@routes_bp.route('/requests/<int:request_id>')
@login_required
def view_request(request_id):
    """View details of a repair request with timeline history."""
    req = query_db(
        """
        SELECT r.*, c.name as category_name, t.name as technician_name, t.phone as technician_phone, u.username as customer_username, u.email as customer_email
        FROM repair_requests r
        JOIN service_categories c ON r.category_id = c.id
        JOIN users u ON r.customer_id = u.id
        LEFT JOIN technicians t ON r.assigned_technician_id = t.id
        WHERE r.id = ?
        """,
        (request_id,),
        one=True
    )
    if req is None:
        flash("Repair request not found.", "danger")
        return redirect(url_for('routes.dashboard'))

    # Customer can only view their own requests
    if g.user_role == 'customer' and req['customer_id'] != g.user['id']:
        flash("Unauthorized access to this repair request.", "danger")
        return redirect(url_for('routes.dashboard'))

    updates = query_db(
        """
        SELECT u.*, usr.username, usr.role as user_role
        FROM request_updates u
        LEFT JOIN users usr ON u.user_id = usr.id
        WHERE u.request_id = ?
        ORDER BY u.created_at ASC
        """,
        (request_id,)
    )

    appointments = query_db(
        """
        SELECT a.*, t.name as technician_name
        FROM appointments a
        JOIN technicians t ON a.technician_id = t.id
        WHERE a.request_id = ?
        ORDER BY a.created_at DESC
        """,
        (request_id,)
    )

    sla_info = calculate_sla_status(req['created_at'], req['priority'], req['resolved_at'])

    return render_template(
        'customer/view_request.html',
        req=req,
        updates=updates,
        appointments=appointments,
        sla=sla_info
    )

@routes_bp.route('/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_request(request_id):
    """Cancel an active repair request."""
    req = query_db("SELECT * FROM repair_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for('routes.dashboard'))

    if g.user_role == 'customer' and req['customer_id'] != g.user['id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('routes.dashboard'))

    if req['status'] in ('RESOLVED', 'CLOSED', 'CANCELLED'):
        flash(f"Cannot cancel a request that is already {req['status']}.", "warning")
        return redirect(url_for('routes.view_request', request_id=request_id))

    reason = request.form.get('cancel_reason', 'Cancelled by customer').strip()
    execute_db(
        "UPDATE repair_requests SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (request_id,)
    )
    execute_db(
        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, 'CANCELLED', ?)",
        (request_id, g.user['id'], req['status'], reason)
    )
    log_activity("REQUEST_CANCELLED", f"Request #{request_id} cancelled. Reason: {reason}", user_id=g.user['id'])
    flash("Repair request has been cancelled.", "info")
    return redirect(url_for('routes.view_request', request_id=request_id))

# ----------------- Service Staff & Admin Triage -----------------

@routes_bp.route('/staff/requests/<int:request_id>/manage', methods=['GET', 'POST'])
@login_required
@role_required(['staff', 'admin'])
def manage_request(request_id):
    """Staff interface to assign technician, schedule appointment, update priority/status."""
    req = query_db(
        """
        SELECT r.*, c.name as category_name, u.username as customer_username, u.email as customer_email
        FROM repair_requests r
        JOIN service_categories c ON r.category_id = c.id
        JOIN users u ON r.customer_id = u.id
        WHERE r.id = ?
        """,
        (request_id,),
        one=True
    )
    if not req:
        flash("Repair request not found.", "danger")
        return redirect(url_for('routes.dashboard'))

    technicians = query_db("SELECT * FROM technicians WHERE is_available = 1 ORDER BY name ASC")
    updates = query_db(
        """
        SELECT u.*, usr.username, usr.role as user_role
        FROM request_updates u
        LEFT JOIN users usr ON u.user_id = usr.id
        WHERE u.request_id = ?
        ORDER BY u.created_at ASC
        """,
        (request_id,)
    )
    appointments = query_db(
        """
        SELECT a.*, t.name as technician_name
        FROM appointments a
        JOIN technicians t ON a.technician_id = t.id
        WHERE a.request_id = ?
        ORDER BY a.created_at DESC
        """,
        (request_id,)
    )
    sla_info = calculate_sla_status(req['created_at'], req['priority'], req['resolved_at'])

    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('notes', '').strip()

        # Action 1: Assign Technician & Update Priority
        if action == 'assign':
            technician_id = request.form.get('technician_id')
            priority = request.form.get('priority', req['priority'])
            if not technician_id:
                flash("Please select a technician to assign.", "danger")
            else:
                sla_target = SLA_TARGET_HOURS.get(priority, 24)
                new_status = 'ASSIGNED' if req['status'] == 'REQUESTED' else req['status']
                execute_db(
                    """
                    UPDATE repair_requests
                    SET assigned_technician_id = ?, priority = ?, sla_target_hours = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (technician_id, priority, sla_target, new_status, request_id)
                )
                tech = query_db("SELECT name FROM technicians WHERE id = ?", (technician_id,), one=True)
                tech_name = tech['name'] if tech else f"Tech #{technician_id}"
                msg = f"Assigned to {tech_name}. Priority set to {priority}. {notes}".strip()
                execute_db(
                    "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?)",
                    (request_id, g.user['id'], req['status'], new_status, msg)
                )
                log_activity("REQUEST_ASSIGNED", f"Request #{request_id} assigned to {tech_name}", user_id=g.user['id'])
                flash(f"Technician {tech_name} assigned successfully.", "success")
                return redirect(url_for('routes.manage_request', request_id=request_id))

        # Action 2: Schedule Appointment
        elif action == 'schedule':
            technician_id = request.form.get('schedule_technician_id') or req['assigned_technician_id']
            appointment_date = request.form.get('appointment_date', '').strip()
            time_slot = request.form.get('time_slot', '').strip()

            if not technician_id:
                flash("Please assign a technician before scheduling an appointment.", "danger")
            elif not appointment_date or not time_slot:
                flash("Appointment date and time slot are required.", "danger")
            else:
                # Check for technician scheduling conflicts
                conflict = query_db(
                    """
                    SELECT id, request_id FROM appointments
                    WHERE technician_id = ? AND appointment_date = ? AND time_slot = ? AND status = 'SCHEDULED'
                    """,
                    (technician_id, appointment_date, time_slot),
                    one=True
                )
                if conflict:
                    flash(f"Technician is already booked for {appointment_date} at {time_slot} (Request #{conflict['request_id']}). Please select another slot.", "danger")
                else:
                    execute_db(
                        "INSERT INTO appointments (request_id, technician_id, appointment_date, time_slot, status, notes) VALUES (?, ?, ?, ?, 'SCHEDULED', ?)",
                        (request_id, technician_id, appointment_date, time_slot, notes)
                    )
                    new_status = 'SCHEDULED' if req['status'] in ('REQUESTED', 'ASSIGNED') else req['status']
                    execute_db(
                        "UPDATE repair_requests SET status = ?, assigned_technician_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_status, technician_id, request_id)
                    )
                    execute_db(
                        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?)",
                        (request_id, g.user['id'], req['status'], new_status, f"Appointment scheduled for {appointment_date} ({time_slot}). {notes}".strip())
                    )
                    log_activity("APPOINTMENT_SCHEDULED", f"Appointment for request #{request_id} scheduled on {appointment_date} {time_slot}", user_id=g.user['id'])
                    flash("Appointment scheduled successfully.", "success")
                    return redirect(url_for('routes.manage_request', request_id=request_id))

        # Action 3: Update Lifecycle Status
        elif action == 'update_status':
            new_status = request.form.get('new_status')
            allowed_next = VALID_STATUS_TRANSITIONS.get(req['status'], [])

            if not new_status or (new_status not in allowed_next and new_status != req['status']):
                flash(f"Invalid transition from {req['status']} to {new_status}. Allowed: {', '.join(allowed_next) or 'None'}", "danger")
            else:
                resolved_timestamp = "CURRENT_TIMESTAMP" if new_status == 'RESOLVED' else "NULL"
                if new_status == 'RESOLVED':
                    execute_db(
                        "UPDATE repair_requests SET status = ?, resolved_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_status, request_id)
                    )
                else:
                    execute_db(
                        "UPDATE repair_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_status, request_id)
                    )

                update_note = notes if notes else f"Status changed to {new_status}"
                execute_db(
                    "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?)",
                    (request_id, g.user['id'], req['status'], new_status, update_note)
                )
                log_activity("STATUS_UPDATED", f"Request #{request_id} status updated from {req['status']} to {new_status}", user_id=g.user['id'])
                flash(f"Status updated to {new_status}.", "success")
                return redirect(url_for('routes.manage_request', request_id=request_id))

        # Action 4: Add Service Note
        elif action == 'add_note':
            if not notes:
                flash("Note content cannot be empty.", "warning")
            else:
                execute_db(
                    "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?)",
                    (request_id, g.user['id'], req['status'], req['status'], f"Note: {notes}")
                )
                flash("Service note added.", "info")
                return redirect(url_for('routes.manage_request', request_id=request_id))

    return render_template(
        'staff/manage_request.html',
        req=req,
        technicians=technicians,
        updates=updates,
        appointments=appointments,
        sla=sla_info,
        allowed_transitions=VALID_STATUS_TRANSITIONS.get(req['status'], [])
    )

# ----------------- Admin Management Routes -----------------

@routes_bp.route('/admin/categories', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_categories():
    """Manage repair service categories."""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            if not name:
                flash("Category name is required.", "danger")
            elif query_db("SELECT id FROM service_categories WHERE name = ?", (name,), one=True):
                flash("A category with this name already exists.", "danger")
            else:
                execute_db("INSERT INTO service_categories (name, description, is_active) VALUES (?, ?, 1)", (name, description))
                log_activity("CATEGORY_CREATED", f"New category created: {name}")
                flash(f"Category '{name}' created successfully.", "success")
        elif action == 'toggle':
            cat_id = request.form.get('category_id')
            current_status = int(request.form.get('current_status', 1))
            new_status = 0 if current_status == 1 else 1
            execute_db("UPDATE service_categories SET is_active = ? WHERE id = ?", (new_status, cat_id))
            flash("Category status updated.", "info")
        return redirect(url_for('routes.admin_categories'))

    categories = query_db("SELECT * FROM service_categories ORDER BY id ASC")
    return render_template('admin/categories.html', categories=categories)

@routes_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_users():
    """Manage user accounts and roles."""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_user':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            role = request.form.get('role', 'staff')
            if not username or not email or not password:
                flash("All fields are required.", "danger")
            elif query_db("SELECT id FROM users WHERE username = ? OR email = ?", (username, email), one=True):
                flash("Username or email is already registered.", "danger")
            else:
                pwd_hash = generate_password_hash(password)
                execute_db("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)", (username, email, pwd_hash, role))
                log_activity("USER_CREATED_BY_ADMIN", f"User {username} ({role}) created by admin")
                flash(f"User '{username}' ({role}) created successfully.", "success")
        return redirect(url_for('routes.admin_users'))

    users = query_db("SELECT id, username, email, role, created_at FROM users ORDER BY id ASC")
    return render_template('admin/users.html', users=users)

@routes_bp.route('/admin/logs')
@login_required
@role_required('admin')
def admin_logs():
    """Review application activity audit trail."""
    event_filter = request.args.get('event_type', '')
    if event_filter:
        logs = query_db(
            """
            SELECT l.*, u.username
            FROM activity_logs l
            LEFT JOIN users u ON l.user_id = u.id
            WHERE l.event_type = ?
            ORDER BY l.created_at DESC LIMIT 100
            """,
            (event_filter,)
        )
    else:
        logs = query_db(
            """
            SELECT l.*, u.username
            FROM activity_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC LIMIT 100
            """
        )
    return render_template('admin/logs.html', logs=logs, event_filter=event_filter)
