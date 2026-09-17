import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_user
from app.domain.user import User
import app.infrastructure.valkey as valkey

router = APIRouter()


@router.get("/raw")
async def get_raw_data_stream(
    current_user: Annotated[User, Depends(get_current_active_user)], limit: int = 100
):
    """
    Fetch the most recent raw ingested data from the Valkey firehose.
    """
    if limit > 500:
        limit = 500

    results = []
    try:
        if valkey.redis is None:
            raise HTTPException(status_code=500, detail="Valkey client not initialized")

        raw_entries = await valkey.redis.lrange("raw_ingestion_feed", 0, limit - 1)
        for entry in raw_entries:
            try:
                parsed = json.loads(entry)
                results.append(parsed)
            except json.JSONDecodeError:
                print(f"Failed to decode entry: {entry}")
                continue
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc(); print(f"Error fetching from Valkey: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while fetching data stream."
        )

    return results


