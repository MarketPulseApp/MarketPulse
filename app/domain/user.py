from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    role: str = "user"


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
