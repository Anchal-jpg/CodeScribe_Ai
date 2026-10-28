import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "CodeScribe AI"
    assert "version" in data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mode" in data


def test_model_status(client):
    response = client.get("/api/model-status")
    assert response.status_code == 200
    data = response.json()
    assert "model_loaded" in data
    assert "trained_model_connected" in data


def test_generate_empty_code_rejected(client):
    response = client.post("/api/generate", json={"code": "   ", "output_mode": "both"})
    assert response.status_code in (400, 422)


def test_generate_unsupported_mode_rejected(client):
    response = client.post("/api/generate", json={"code": "def foo(): pass", "output_mode": "invalid_mode"})
    assert response.status_code == 422 or response.status_code == 400


def test_generate_valid_code(client):
    response = client.post(
        "/api/generate",
        json={"code": "def greet(name):\n    return f'Hello, {name}'", "output_mode": "both"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["output_mode"] == "both"
    assert data["docstring"] is not None
    assert data["explanation"] is not None
    assert data["model_loaded"] in (True, False)
    assert "status" in data
