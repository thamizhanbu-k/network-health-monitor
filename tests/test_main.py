import pytest
import sys
import os

# Ensure the app module can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'app' in data
    assert 'timestamp' in data

def test_status_endpoint(client):
    response = client.get('/status')
    assert response.status_code == 200
    data = response.get_json()
    assert 'app' in data
    assert 'version' in data

def test_index_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data
    assert 'endpoints' in data