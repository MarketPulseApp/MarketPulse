import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_current_active_user, get_user_repository
from app.core.services.auth_service import AuthService
from app.db.postgres.user import UserRepository
from app.domain.user import User, UserCreate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login")
async def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    auth_service = AuthService(user_repo)
    user = await auth_service.authenticate_user(
        email=form_data.username, password=form_data.password
    )

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return {
        "access_token": auth_service.create_token_for_user(user),
        "token_type": "bearer",
    }


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate, user_repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> User:
    """
    Register a new user.
    """
    logger.info(f"Received registration request for email: {user_in.email}")
    auth_service = AuthService(user_repo)
    try:
        user = await auth_service.register_user(email=user_in.email, password=user_in.password)
        logger.info(f"Successfully registered user with email: {user_in.email}")
        return user
    except ValueError as e:
        logger.error(f"ValueError during registration for {user_in.email}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during registration for {user_in.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
    """
    Get current user.
    """
    return current_user
