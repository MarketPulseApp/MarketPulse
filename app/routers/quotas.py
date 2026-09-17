from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_active_user, get_quota_repository
from app.core.encryption import decrypt_value, encrypt_value
from app.db.postgres.quota import QuotaRepository
from app.domain.user import User

router = APIRouter()


class QuotaResponse(BaseModel):
    source_name: str
    daily_used: int
    monthly_used: int
    is_unlimited: bool
    daily_limit: int | None
    monthly_limit: int | None
    api_key_masked: str | None


class QuotaUpdateRequest(BaseModel):
    daily_limit: int | None = None
    monthly_limit: int | None = None
    api_key: str | None = None


class QuotaCreateRequest(BaseModel):
    source_name: str
    daily_limit: int | None = None
    monthly_limit: int | None = None
    api_key: str | None = None


@router.get("", response_model=list[QuotaResponse])
async def get_all_quotas(
    quota_repo: Annotated[QuotaRepository, Depends(get_quota_repository)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    quotas = await quota_repo.get_all()
    results = []
    for q in quotas:
        masked = None
        if q.api_key:
            decrypted = decrypt_value(q.api_key)
            if decrypted:
                masked = f"***{decrypted[-4:]}" if len(decrypted) > 4 else "***"
        results.append(
            QuotaResponse(
                source_name=q.source_name,
                daily_used=q.daily_used,
                monthly_used=q.monthly_used,
                is_unlimited=q.is_unlimited,
                daily_limit=q.daily_limit,
                monthly_limit=q.monthly_limit,
                api_key_masked=masked,
            )
        )
    return results


@router.post("", response_model=QuotaResponse)
async def create_quota(
    create_req: QuotaCreateRequest,
    quota_repo: Annotated[QuotaRepository, Depends(get_quota_repository)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    api_key_encrypted = None
    if create_req.api_key:
        api_key_encrypted = encrypt_value(create_req.api_key)
        from app.infrastructure.valkey import redis

        if redis:
            await redis.set(f"api_key:{create_req.source_name}", create_req.api_key)

    await quota_repo.create_quota(
        create_req.source_name, create_req.daily_limit, create_req.monthly_limit, api_key_encrypted
    )

    updated = await quota_repo.get_by_source(create_req.source_name)
    if not updated:
        raise HTTPException(status_code=500, detail="Error creating quota")

    masked = None
    if updated.api_key:
        decrypted = decrypt_value(updated.api_key)
        if decrypted:
            masked = f"***{decrypted[-4:]}" if len(decrypted) > 4 else "***"

    return QuotaResponse(
        source_name=updated.source_name,
        daily_used=updated.daily_used,
        monthly_used=updated.monthly_used,
        is_unlimited=updated.is_unlimited,
        daily_limit=updated.daily_limit,
        monthly_limit=updated.monthly_limit,
        api_key_masked=masked,
    )


@router.put("/{source_name}", response_model=QuotaResponse)
async def update_quota(
    source_name: str,
    update_req: QuotaUpdateRequest,
    quota_repo: Annotated[QuotaRepository, Depends(get_quota_repository)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    existing = await quota_repo.get_by_source(source_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Quota not found")

    new_api_key_encrypted = existing.api_key
    if update_req.api_key and not update_req.api_key.startswith("***"):
        new_api_key_encrypted = encrypt_value(update_req.api_key)
        from app.infrastructure.valkey import redis

        if redis:
            await redis.set(f"api_key:{source_name}", update_req.api_key)

    await quota_repo.update_quota(
        source_name, update_req.daily_limit, update_req.monthly_limit, new_api_key_encrypted
    )

    updated = await quota_repo.get_by_source(source_name)
    if not updated:
        raise HTTPException(status_code=404, detail="Error fetching updated quota")

    masked = None
    if updated.api_key:
        decrypted = decrypt_value(updated.api_key)
        if decrypted:
            masked = f"***{decrypted[-4:]}" if len(decrypted) > 4 else "***"

    return QuotaResponse(
        source_name=updated.source_name,
        daily_used=updated.daily_used,
        monthly_used=updated.monthly_used,
        is_unlimited=updated.is_unlimited,
        daily_limit=updated.daily_limit,
        monthly_limit=updated.monthly_limit,
        api_key_masked=masked,
    )
