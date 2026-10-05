"""Health check endpoint tests."""

import json

def test_health_check_endpoint(client):
    """Verify /health returns 200 and healthy JSON status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert data['status'] == 'healthy'
    assert data['database'] == 'connected'
    assert 'timestamp' in data
