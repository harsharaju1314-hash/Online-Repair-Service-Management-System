"""Pytest fixtures and configuration."""

import os
import sys
import tempfile
import pytest

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.db import init_db, seed_db, get_db

@pytest.fixture
def app():
    """Create and configure a Flask application instance for testing."""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'SECRET_KEY': 'test-secret-key-12345'
    })

    with app.app_context():
        init_db()
        seed_db()

    yield app

    # Cleanup temporary database file
    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

class AuthActions:
    """Helper class for logging in as different user roles during tests."""
    def __init__(self, client):
        self._client = client

    def login(self, username='customer1', password='customer123'):
        return self._client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def login_staff(self):
        return self.login(username='staff1', password='staff123')

    def login_admin(self):
        return self.login(username='admin', password='admin123')

    def logout(self):
        return self._client.get('/logout', follow_redirects=True)

@pytest.fixture
def auth(client):
    return AuthActions(client)
