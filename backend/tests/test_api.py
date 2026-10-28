import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_api_health():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mode"] == "local-first"

def test_system_info():
    client = TestClient(app)
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "os" in data
    assert "total_ram_gb" in data

def test_list_backends():
    client = TestClient(app)
    response = client.get("/api/backends")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_list_datasets():
    client = TestClient(app)
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8

def test_backend_health_fake():
    client = TestClient(app)
    response = client.get("/api/backends/backend_fake/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["testing_only"] is True
