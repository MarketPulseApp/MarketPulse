from pydantic import BaseModel


class SystemSettings(BaseModel):
    id: int
    active_strategy: str
    confidence_threshold: float


class SystemSettingsUpdate(BaseModel):
    active_strategy: str
    confidence_threshold: float
