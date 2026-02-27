"""
Auth service: credentials, JWT, and user lookup.
"""

from typing import Optional
from jose import JWTError, jwt

from src.core.helper import get_jwt_public_key, settings
from src.core.security import verify_password, get_password_hash, create_access_token
from src.dtos.auth import Token, UserOut
from src.events import UserCreatedEvent, publisher
from src.models.auth import User
from src.repositories.base_auth_repo import BaseAuthRepository

class AuthService:
    """Auth operations: register, login, token validation."""
    def __init__(self, repo: BaseAuthRepository) -> None:
        self.repo = repo

    def authenticate_user(
        self,
        username_or_email: str,
        password: str,
    ) -> Optional[User]:
        key = username_or_email.strip() if username_or_email else ""
        if not key:
            return None
        user = self.repo.get_by_username(key)
        if user is None:
            user = self.repo.get_by_email(key)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user

    async def register(
        self,
        username: str,
        email: str,
        password: str,
    ) -> UserOut:
        if self.repo.username_exists(username):
            raise ValueError("Username already registered")
        hashed = get_password_hash(password)
        user = self.repo.create_user(username, email, hashed)
        await publisher.publish_user_created(
            UserCreatedEvent(user_id=user.username, username=user.username, email=user.email)
        )
        return UserOut(username=user.username, email=user.email)

    def login(
        self,
        username: str,
        password: str,
    ) -> Token:
        user = self.authenticate_user(username, password)
        if not user:
            raise ValueError("Incorrect username or password")
        access_token = create_access_token(data={"sub": user.username})
        return Token(access_token=access_token)

    def get_current_user_from_token(
        self,
        token: str,
    ) -> UserOut:
        public_key = get_jwt_public_key()
        if not public_key:
            raise ValueError("JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH must be set for RS256")
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[settings.JWT_ALGORITHM],
            )
            username: Optional[str] = payload.get("sub")
            if username is None:
                raise ValueError("Invalid token")
        except JWTError:
            raise ValueError("Could not validate credentials")
        user = self.repo.get_by_username(username)
        if user is None:
            raise ValueError("User not found")
        return UserOut(username=user.username, email=user.email)

    async def login_or_register_oidc(
        self,
        provider: str,
        subject_id: str,
        email: str,
        name: str,
    ) -> tuple[UserOut, Token, bool]:
        """
        Find or create user by OIDC identity. Returns (UserOut, Token, is_new_user).
        Publishes UserCreated only when is_new_user.
        """
        existing = self.repo.get_by_federated(provider, subject_id)
        if existing:
            access_token = create_access_token(data={"sub": existing.username})
            return (
                UserOut(username=existing.username, email=existing.email),
                Token(access_token=access_token),
                False,
            )

        base_username = (email or name or subject_id).split("@")[0].replace(".", "_")[:64]
        username = base_username
        idx = 0
        while self.repo.username_exists(username):
            idx += 1
            username = f"{base_username}_{idx}"

        user = self.repo.create_federated_user(provider, subject_id, username, email or "")
        await publisher.publish_user_created(
            UserCreatedEvent(user_id=user.username, username=user.username, email=email or "")
        )
        access_token = create_access_token(data={"sub": user.username})
        return (
            UserOut(username=user.username, email=user.email),
            Token(access_token=access_token),
            True,
        )