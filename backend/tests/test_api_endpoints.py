import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.seed import seed_database, create_sample_road_image
import io

seed_database()
client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["cv_engine"] == "READY"

def test_auth_demo_switch():
    response = client.post("/api/v1/auth/demo-switch", json={"role": "ADMIN"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"

def test_list_hazards():
    response = client.get("/api/v1/hazards")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1

def test_map_hazards():
    response = client.get("/api/v1/map/hazards")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data

def test_maintenance_queue():
    response = client.get("/api/v1/maintenance/queue")
    assert response.status_code == 200
    data = response.json()
    assert "queue" in data

def test_ai_assistant_chat():
    response = client.post("/api/v1/ai/chat", json={"query": "Show critical road hazards"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["tool_called"] is not None

def test_analytics_overview():
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_hazards" in data
    assert "resolution_rate_pct" in data
