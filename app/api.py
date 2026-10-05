from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, g
from app.auth import login_required, role_required, log_activity
from app.db import query_db, execute_db
from app.sla import calculate_sla_status, SLA_TARGET_HOURS

api_bp = Blueprint('api', __name__, url_prefix='/api')

VALID_STATUS_TRANSITIONS = {
    'REQUESTED': ['ASSIGNED', 'CANCELLED'],
    'ASSIGNED': ['SCHEDULED', 'IN_PROGRESS', 'CANCELLED'],
    'SCHEDULED': ['IN_PROGRESS', 'CANCELLED'],
    'IN_PROGRESS': ['RESOLVED', 'CANCELLED'],
    'RESOLVED': ['CLOSED', 'IN_PROGRESS'],
    'CLOSED': [],
    'CANCELLED': []
}

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """List active service categories."""
    categories = query_db("SELECT id, name, description, is_active FROM service_categories WHERE is_active = 1")
    return jsonify([dict(c) for c in categories]), 200

@api_bp.route('/technicians', methods=['GET'])
@login_required
@role_required(['staff', 'admin'])
def get_technicians():
    """List all available technicians."""
    technicians = query_db("SELECT id, name, email, phone, specialization, is_available FROM technicians")
    return jsonify([dict(t) for t in technicians]), 200

@api_bp.route('/requests', methods=['GET'])
@login_required
def list_requests():
    """List repair requests according to user role."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if g.user_role == 'customer':
        rows = query_db(
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
    else:
        rows = query_db(
            """
            SELECT r.*, c.name as category_name, t.name as technician_name, u.username as customer_username
            FROM repair_requests r
            JOIN service_categories c ON r.category_id = c.id
            JOIN users u ON r.customer_id = u.id
            LEFT JOIN technicians t ON r.assigned_technician_id = t.id
            ORDER BY r.created_at DESC
            """
        )

    results = []
    for r in rows:
        item = dict(r)
        item['sla'] = calculate_sla_status(r['created_at'], r['priority'], r['resolved_at'], now)
        results.append(item)

    return jsonify(results), 200

@api_bp.route('/requests', methods=['POST'])
@login_required
@role_required(['customer', 'admin'])
def create_request():
    """Submit a new repair request."""
    data = request.get_json() or {}
    category_id = data.get('category_id')
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    preferred_date = data.get('preferred_date', '').strip()
    preferred_time_slot = data.get('preferred_time_slot', '').strip()

    if not category_id or not title or not description or not preferred_date or not preferred_time_slot:
        return jsonify({"error": "Missing required fields: category_id, title, description, preferred_date, preferred_time_slot"}), 400

    # Validate category exists
    cat = query_db("SELECT id FROM service_categories WHERE id = ? AND is_active = 1", (category_id,), one=True)
    if not cat:
        return jsonify({"error": "Invalid or inactive service category ID"}), 400

    priority = 'MEDIUM'
    sla_target = SLA_TARGET_HOURS.get(priority, 24)
    result = execute_db(
        """
        INSERT INTO repair_requests (customer_id, category_id, priority, status, title, description, preferred_date, preferred_time_slot, sla_target_hours)
        VALUES (?, ?, ?, 'REQUESTED', ?, ?, ?, ?, ?)
        """,
        (g.user['id'], category_id, priority, title, description, preferred_date, preferred_time_slot, sla_target)
    )
    req_id = result['lastrowid']

    execute_db(
        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, NULL, 'REQUESTED', 'Request created via REST API')",
        (req_id, g.user['id'])
    )
    log_activity("API_REQUEST_CREATED", f"API: Created request #{req_id}", user_id=g.user['id'])

    return jsonify({
        "message": "Repair request created successfully",
        "request_id": req_id,
        "status": "REQUESTED"
    }), 201

@api_bp.route('/requests/<int:request_id>', methods=['GET'])
@login_required
def get_request(request_id):
    """Retrieve details of a single request."""
    req = query_db(
        """
        SELECT r.*, c.name as category_name, t.name as technician_name, u.username as customer_username
        FROM repair_requests r
        JOIN service_categories c ON r.category_id = c.id
        JOIN users u ON r.customer_id = u.id
        LEFT JOIN technicians t ON r.assigned_technician_id = t.id
        WHERE r.id = ?
        """,
        (request_id,),
        one=True
    )
    if not req:
        return jsonify({"error": "Repair request not found"}), 404

    if g.user_role == 'customer' and req['customer_id'] != g.user['id']:
        return jsonify({"error": "Unauthorized access to this resource"}), 403

    updates = query_db("SELECT * FROM request_updates WHERE request_id = ? ORDER BY created_at ASC", (request_id,))
    appointments = query_db("SELECT * FROM appointments WHERE request_id = ? ORDER BY created_at DESC", (request_id,))

    response_data = dict(req)
    response_data['sla'] = calculate_sla_status(req['created_at'], req['priority'], req['resolved_at'])
    response_data['history'] = [dict(u) for u in updates]
    response_data['appointments'] = [dict(a) for a in appointments]

    return jsonify(response_data), 200

@api_bp.route('/requests/<int:request_id>', methods=['PUT'])
@login_required
@role_required(['staff', 'admin'])
def update_request(request_id):
    """Update title, description, or priority."""
    req = query_db("SELECT * FROM repair_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        return jsonify({"error": "Repair request not found"}), 404

    data = request.get_json() or {}
    title = data.get('title', req['title']).strip()
    description = data.get('description', req['description']).strip()
    priority = data.get('priority', req['priority']).upper()

    if priority not in ('LOW', 'MEDIUM', 'HIGH'):
        return jsonify({"error": "Invalid priority. Must be LOW, MEDIUM, or HIGH"}), 400

    sla_target = SLA_TARGET_HOURS.get(priority, 24)
    execute_db(
        "UPDATE repair_requests SET title = ?, description = ?, priority = ?, sla_target_hours = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, description, priority, sla_target, request_id)
    )
    log_activity("API_REQUEST_UPDATED", f"API: Updated request #{request_id}", user_id=g.user['id'])

    return jsonify({"message": "Request updated successfully", "request_id": request_id, "priority": priority}), 200

@api_bp.route('/requests/<int:request_id>/assign', methods=['POST'])
@login_required
@role_required(['staff', 'admin'])
def assign_technician(request_id):
    """Assign a technician to a request."""
    req = query_db("SELECT * FROM repair_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        return jsonify({"error": "Repair request not found"}), 404

    data = request.get_json() or {}
    technician_id = data.get('technician_id')
    priority = data.get('priority', req['priority']).upper()

    if not technician_id:
        return jsonify({"error": "technician_id is required"}), 400

    tech = query_db("SELECT * FROM technicians WHERE id = ? AND is_available = 1", (technician_id,), one=True)
    if not tech:
        return jsonify({"error": "Technician not found or currently unavailable"}), 404

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
    execute_db(
        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?)",
        (request_id, g.user['id'], req['status'], new_status, f"Assigned to {tech['name']} via API")
    )
    log_activity("API_REQUEST_ASSIGNED", f"API: Assigned request #{request_id} to technician {tech['name']}", user_id=g.user['id'])

    return jsonify({
        "message": "Technician assigned successfully",
        "request_id": request_id,
        "assigned_technician_id": technician_id,
        "status": new_status
    }), 200

@api_bp.route('/requests/<int:request_id>/resolve', methods=['POST'])
@login_required
@role_required(['staff', 'admin'])
def resolve_request(request_id):
    """Mark a request as RESOLVED."""
    req = query_db("SELECT * FROM repair_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        return jsonify({"error": "Repair request not found"}), 404

    allowed_next = VALID_STATUS_TRANSITIONS.get(req['status'], [])
    if 'RESOLVED' not in allowed_next:
        return jsonify({"error": f"Cannot transition from {req['status']} to RESOLVED"}), 400

    data = request.get_json() or {}
    notes = data.get('notes', 'Resolved via API')

    execute_db(
        "UPDATE repair_requests SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (request_id,)
    )
    execute_db(
        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, 'RESOLVED', ?)",
        (request_id, g.user['id'], req['status'], notes)
    )
    log_activity("API_REQUEST_RESOLVED", f"API: Request #{request_id} marked as RESOLVED", user_id=g.user['id'])

    return jsonify({"message": "Request marked as RESOLVED", "request_id": request_id, "status": "RESOLVED"}), 200

@api_bp.route('/requests/<int:request_id>/status', methods=['POST'])
@login_required
@role_required(['staff', 'admin'])
def update_status(request_id):
    """Update status of a request following valid transition paths."""
    req = query_db("SELECT * FROM repair_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        return jsonify({"error": "Repair request not found"}), 404

    data = request.get_json() or {}
    new_status = data.get('status', '').upper()
    notes = data.get('notes', f'Status transition to {new_status} via API')

    allowed_next = VALID_STATUS_TRANSITIONS.get(req['status'], [])
    if new_status not in allowed_next:
        return jsonify({"error": f"Invalid transition from {req['status']} to {new_status}. Allowed: {allowed_next}"}), 400

    resolved_clause = ", resolved_at = CURRENT_TIMESTAMP" if new_status == 'RESOLVED' else ""
    execute_db(
        f"UPDATE repair_requests SET status = ? {resolved_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, request_id)
    )
    execute_db(
        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?)",
        (request_id, g.user['id'], req['status'], new_status, notes)
    )
    log_activity("API_STATUS_CHANGED", f"API: Request #{request_id} moved to {new_status}", user_id=g.user['id'])

    return jsonify({"message": f"Status updated to {new_status}", "request_id": request_id, "status": new_status}), 200

@api_bp.route('/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_request(request_id):
    """Cancel a request."""
    req = query_db("SELECT * FROM repair_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        return jsonify({"error": "Repair request not found"}), 404

    if g.user_role == 'customer' and req['customer_id'] != g.user['id']:
        return jsonify({"error": "Unauthorized action"}), 403

    if req['status'] in ('RESOLVED', 'CLOSED', 'CANCELLED'):
        return jsonify({"error": f"Cannot cancel request in {req['status']} status"}), 400

    data = request.get_json() or {}
    notes = data.get('notes', 'Cancelled via API')

    execute_db(
        "UPDATE repair_requests SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (request_id,)
    )
    execute_db(
        "INSERT INTO request_updates (request_id, user_id, previous_status, new_status, notes) VALUES (?, ?, ?, 'CANCELLED', ?)",
        (request_id, g.user['id'], req['status'], notes)
    )
    log_activity("API_REQUEST_CANCELLED", f"API: Request #{request_id} cancelled", user_id=g.user['id'])

    return jsonify({"message": "Request cancelled successfully", "request_id": request_id, "status": "CANCELLED"}), 200
