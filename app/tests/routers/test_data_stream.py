import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_raw_data_stream_firehose():
    mock_redis = AsyncMock()
    mock_redis.lrange.return_value = [
        json.dumps(
            {
                "source": "Mock_Source",
                "timestamp": "2026-09-17T00:00:00Z",
                "type": "price",
                "payload": {"open": 100},
            }
        )
    ]

    with patch("app.infrastructure.valkey.redis", new=mock_redis):
        response = client.get("/api/v1/data-stream/raw")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "Mock_Source"
        assert data[0]["type"] == "price"
        assert data[0]["payload"]["open"] == 100
