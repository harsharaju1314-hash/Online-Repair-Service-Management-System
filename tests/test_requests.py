"""Repair request lifecycle, dispatch, and validation tests."""

def test_customer_create_request_success(client, auth):
    """Test customer creating a repair request."""
    auth.login('customer1', 'customer123')
    response = client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Refrigerator cooling issue',
        'description': 'Temperature in main cabinet is above 12 degrees Celsius.',
        'preferred_date': '2026-10-15',
        'preferred_time_slot': '09:00 AM - 12:00 PM'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"submitted successfully" in response.data

def test_customer_create_request_invalid_input(client, auth):
    """Test validation rejection when description is too short."""
    auth.login('customer1', 'customer123')
    response = client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Too short',
        'description': 'short',
        'preferred_date': '2026-10-15',
        'preferred_time_slot': '09:00 AM - 12:00 PM'
    }, follow_redirects=True)
    assert b"Description must provide at least 10 characters" in response.data

def test_staff_assign_technician_and_priority(client, auth):
    """Test staff assigning a technician and setting HIGH priority."""
    # First create request as customer
    auth.login('customer1', 'customer123')
    client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Oven heating element broken',
        'description': 'Top heating coil does not glow or warm up.',
        'preferred_date': '2026-10-16',
        'preferred_time_slot': '12:00 PM - 03:00 PM'
    })
    auth.logout()

    # Now login as staff to assign
    auth.login_staff()
    response = client.post('/staff/requests/1/manage', data={
        'action': 'assign',
        'technician_id': 1,
        'priority': 'HIGH',
        'notes': 'Assigned to Alex Johnson for priority diagnostic'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"assigned successfully" in response.data

def test_staff_appointment_scheduling_and_conflict_check(client, auth):
    """Test appointment booking and prevention of double-booking same technician."""
    auth.login('customer1', 'customer123')
    # Create request 1
    client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Dishwasher pump malfunction',
        'description': 'Water not draining after cycle finishes.',
        'preferred_date': '2026-10-17',
        'preferred_time_slot': '09:00 AM - 12:00 PM'
    })
    # Create request 2
    client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Microwave turntable stuck',
        'description': 'Motor buzzing and tray does not spin.',
        'preferred_date': '2026-10-17',
        'preferred_time_slot': '09:00 AM - 12:00 PM'
    })
    auth.logout()

    auth.login_staff()
    # Assign and Schedule request 1 for Tech 1 on 2026-10-17 09:00 AM - 12:00 PM
    client.post('/staff/requests/1/manage', data={
        'action': 'assign',
        'technician_id': 1,
        'priority': 'MEDIUM'
    })
    res_sched1 = client.post('/staff/requests/1/manage', data={
        'action': 'schedule',
        'schedule_technician_id': 1,
        'appointment_date': '2026-10-17',
        'time_slot': '09:00 AM - 12:00 PM',
        'notes': 'Morning slot'
    }, follow_redirects=True)
    assert b"Appointment scheduled successfully" in res_sched1.data

    # Attempt to schedule request 2 with same Tech 1 on same date and time slot -> should conflict
    client.post('/staff/requests/2/manage', data={
        'action': 'assign',
        'technician_id': 1,
        'priority': 'MEDIUM'
    })
    res_conflict = client.post('/staff/requests/2/manage', data={
        'action': 'schedule',
        'schedule_technician_id': 1,
        'appointment_date': '2026-10-17',
        'time_slot': '09:00 AM - 12:00 PM',
        'notes': 'Conflicting slot'
    }, follow_redirects=True)
    assert b"already booked" in res_conflict.data

def test_request_lifecycle_valid_transitions(client, auth):
    """Test full valid lifecycle: REQUESTED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED."""
    auth.login('customer1', 'customer123')
    client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Freezer fan replacement',
        'description': 'Fan making loud grinding noise.',
        'preferred_date': '2026-10-18',
        'preferred_time_slot': '03:00 PM - 06:00 PM'
    })
    auth.logout()

    auth.login_staff()
    # 1. Assign (REQUESTED -> ASSIGNED)
    client.post('/staff/requests/1/manage', data={'action': 'assign', 'technician_id': 1, 'priority': 'HIGH'})

    # 2. Advance to IN_PROGRESS
    res_prog = client.post('/staff/requests/1/manage', data={
        'action': 'update_status',
        'new_status': 'IN_PROGRESS',
        'notes': 'Technician arrived on site'
    }, follow_redirects=True)
    assert b"Status updated to IN_PROGRESS" in res_prog.data

    # 3. Advance to RESOLVED
    res_res = client.post('/staff/requests/1/manage', data={
        'action': 'update_status',
        'new_status': 'RESOLVED',
        'notes': 'Fan replaced and verified'
    }, follow_redirects=True)
    assert b"Status updated to RESOLVED" in res_res.data

    # 4. Close request (RESOLVED -> CLOSED)
    res_closed = client.post('/staff/requests/1/manage', data={
        'action': 'update_status',
        'new_status': 'CLOSED',
        'notes': 'Customer signature captured and invoice settled.'
    }, follow_redirects=True)
    assert b"Status updated to CLOSED" in res_closed.data

def test_invalid_status_transition_rejected(client, auth):
    """Test that skipping steps (e.g. REQUESTED -> RESOLVED) is rejected."""
    auth.login('customer1', 'customer123')
    client.post('/requests/new', data={
        'category_id': 1,
        'title': 'Direct resolve attempt',
        'description': 'Attempting invalid status transition skipping triage.',
        'preferred_date': '2026-10-19',
        'preferred_time_slot': '09:00 AM - 12:00 PM'
    })
    auth.logout()

    auth.login_staff()
    res = client.post('/staff/requests/1/manage', data={
        'action': 'update_status',
        'new_status': 'RESOLVED',
        'notes': 'Skipping assignment and progress'
    }, follow_redirects=True)
    assert b"Invalid transition from REQUESTED to RESOLVED" in res.data
