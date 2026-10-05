"""Authentication and authorization tests."""

def test_registration_success(client):
    """Test new customer registration."""
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration successful" in response.data

def test_registration_duplicate_username(client):
    """Test registration failure when username exists."""
    response = client.post('/register', data={
        'username': 'customer1',
        'email': 'different@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b"already taken" in response.data

def test_registration_password_mismatch(client):
    """Test registration failure on mismatched passwords."""
    response = client.post('/register', data={
        'username': 'validuser',
        'email': 'valid@example.com',
        'password': 'password123',
        'confirm_password': 'password999'
    }, follow_redirects=True)
    assert b"Passwords do not match" in response.data

def test_login_success_and_logout(client, auth):
    """Test successful customer login and subsequent logout."""
    res_login = auth.login('customer1', 'customer123')
    assert res_login.status_code == 200
    assert b"Welcome back, customer1" in res_login.data

    res_logout = auth.logout()
    assert res_logout.status_code == 200
    assert b"successfully logged out" in res_logout.data

def test_login_invalid_credentials(client, auth):
    """Test login rejection for wrong password."""
    response = auth.login('customer1', 'wrongpassword')
    assert b"Invalid username/email or password" in response.data

def test_unauthenticated_access_redirects(client):
    """Test unauthenticated user accessing protected dashboard gets redirected."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
