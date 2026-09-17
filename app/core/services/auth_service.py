import logging
import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.postgres.user import UserRepository
from app.domain.user import User

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def register_user(self, email: str, password: str) -> User:
        """
        Register a new user in the system.

        Args:
            email (str): The email address for the user.
            password (str): The plaintext password.

        Returns:
            User: The newly created user domain object.

        Raises:
            ValueError: If a user with the given email already exists.
        """
        logger.debug(
            f"AuthService.register_user: Checking if user with email {email} already exists"
        )
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            logger.warning(f"AuthService.register_user: User with email {email} already exists")
            raise ValueError("User with this email already exists")

        logger.debug(f"AuthService.register_user: Creating new user with email {email}")
        now = datetime.now(UTC)
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(password)

        new_user = User(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            role="user",
            created_at=now,
            updated_at=now,
        )
        logger.debug("AuthService.register_user: Saving new user to repository")
        created_user = await self.user_repo.create(new_user)
        logger.debug(f"AuthService.register_user: Successfully saved new user {user_id}")
        return created_user

    def create_token_for_user(self, user: User) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token({"sub": str(user.id)}, expires_delta=access_token_expires)
