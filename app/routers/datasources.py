from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.plugins.datasources.registry import register_datasource

router = APIRouter()


class CustomDataSource(BaseModel):
    source_name: str
    type: str  # "rest_api" or "rss"
    url: str
    token: str | None = None
    daily_limit: int | None = None
    record_type: str | None = "data"
    enabled: bool = True


@router.post("/")
async def add_custom_datasource(source: CustomDataSource) -> dict[str, Any]:
    """
    Registers a new data ingestion source dynamically via the UI.
    """
    if source.type not in ["rest_api", "rss"]:
        raise HTTPException(
            status_code=400, detail="Invalid source type. Must be 'rest_api' or 'rss'."
        )

    config: dict[str, Any] = {"type": source.type, "url": source.url, "enabled": source.enabled}

    if source.type == "rest_api":
        config["token"] = source.token
        config["daily_limit"] = source.daily_limit
        config["record_type"] = source.record_type

    await register_datasource(source.source_name, config)
    return {
        "status": "success",
        "message": f"Data source '{source.source_name}' registered successfully.",
    }
