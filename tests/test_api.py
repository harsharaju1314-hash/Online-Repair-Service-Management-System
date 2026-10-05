"""REST API endpoint tests."""

import json

def test_api_get_categories(client):
    """Test public categories endpoint."""
    response = client.get('/api/categories')
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert isinstance(data, list)
    assert len(data) >= 4
    assert any(c['name'] == 'Appliance Repair' for c in data)

def test_api_create_request_authenticated(client, auth):
    """Test creating a request via POST /api/requests."""
    auth.login('customer1', 'customer123')
    payload = {
        "category_id": 1,
        "title": "API Test Request",
        "description": "Created through REST API test case with detailed description",
        "preferred_date": "2026-10-20",
        "preferred_time_slot": "09:00 AM - 12:00 PM"
    }
    response = client.post('/api/requests', json=payload)
    assert response.status_code == 201
    data = json.loads(response.data.decode('utf-8'))
    assert data['status'] == 'REQUESTED'
    assert 'request_id' in data

def test_api_create_request_unauthenticated(client):
    """Test rejection with 401 when creating request unauthenticated."""
    payload = {
        "category_id": 1,
        "title": "Unauthenticated Request",
        "description": "Should fail",
        "preferred_date": "2026-10-20",
        "preferred_time_slot": "09:00 AM - 12:00 PM"
    }
    response = client.post('/api/requests', json=payload)
    assert response.status_code == 401

def test_api_assign_and_resolve_flow(client, auth):
    """Test API assignment and resolution workflow."""
    # 1. Customer creates request
    auth.login('customer1', 'customer123')
    res_create = client.post('/api/requests', json={
        "category_id": 1,
        "title": "Water heater leaking",
        "description": "Continuous slow drip from drain valve",
        "preferred_date": "2026-10-21",
        "preferred_time_slot": "12:00 PM - 03:00 PM"
    })
    req_id = json.loads(res_create.data.decode('utf-8'))['request_id']
    auth.logout()

    # 2. Staff assigns technician via API
    auth.login_staff()
    res_assign = client.post(f'/api/requests/{req_id}/assign', json={
        "technician_id": 2,
        "priority": "HIGH"
    })
    assert res_assign.status_code == 200
    data_assign = json.loads(res_assign.data.decode('utf-8'))
    assert data_assign['status'] == 'ASSIGNED'
    assert data_assign['assigned_technician_id'] == 2

    # 3. Staff advances status to IN_PROGRESS
    res_prog = client.post(f'/api/requests/{req_id}/status', json={
        "status": "IN_PROGRESS",
        "notes": "Technician started repair work"
    })
    assert res_prog.status_code == 200

    # 4. Staff marks RESOLVED
    res_res = client.post(f'/api/requests/{req_id}/resolve', json={
        "notes": "Valve replaced successfully"
    })
    assert res_res.status_code == 200
    data_res = json.loads(res_res.data.decode('utf-8'))
    assert data_res['status'] == 'RESOLVED'

    # 5. Get request details
    res_get = client.get(f'/api/requests/{req_id}')
    assert res_get.status_code == 200
    data_get = json.loads(res_get.data.decode('utf-8'))
    assert data_get['status'] == 'RESOLVED'
    assert data_get['sla']['priority'] == 'HIGH'
