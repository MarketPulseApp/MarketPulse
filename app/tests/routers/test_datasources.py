from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.datasources import router

app = FastAPI()
app.include_router(router, prefix="/api/v1/datasources")

client = TestClient(app)


@patch("app.routers.datasources.register_datasource")
def test_add_custom_datasource_valid_rest_api(mock_register):
    payload = {
        "source_name": "MyRestAPI",
        "type": "rest_api",
        "url": "https://api.example.com/data",
        "token": "secret-token",
        "daily_limit": 100,
        "record_type": "data",
        "enabled": True,
    }

    response = client.post("/api/v1/datasources/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Data source 'MyRestAPI' registered successfully."

    mock_register.assert_called_once_with(
        "MyRestAPI",
        {
            "type": "rest_api",
            "url": "https://api.example.com/data",
            "enabled": True,
            "token": "secret-token",
            "daily_limit": 100,
            "record_type": "data",
        },
    )


def test_add_custom_datasource_invalid_type():
    payload = {
        "source_name": "GarbageSource",
        "type": "garbage",
        "url": "https://garbage.example.com",
    }

    response = client.post("/api/v1/datasources/", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "Invalid source type. Must be 'rest_api' or 'rss'." in data["detail"]
