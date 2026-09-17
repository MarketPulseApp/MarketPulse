from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_user, get_system_settings_repository
from app.db.postgres.system_settings import SystemSettingsRepository
from app.domain.system_settings import SystemSettings, SystemSettingsUpdate
from app.domain.user import User

router = APIRouter()


@router.get("/trading", response_model=SystemSettings)
async def get_trading_settings(
    settings_repo: Annotated[SystemSettingsRepository, Depends(get_system_settings_repository)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    settings = await settings_repo.get_settings()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings


@router.put("/trading", response_model=SystemSettings)
async def update_trading_settings(
    settings_update: SystemSettingsUpdate,
    settings_repo: Annotated[SystemSettingsRepository, Depends(get_system_settings_repository)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    # Depending on requirements, we might want to restrict this to admins
    # but for now we follow the user prompt which didn't specify roles.
    # However we can add get_current_active_superuser if needed.
    settings = await settings_repo.update_settings(
        active_strategy=settings_update.active_strategy,
        confidence_threshold=settings_update.confidence_threshold,
    )
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings
