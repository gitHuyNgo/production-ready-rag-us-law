from abc import ABC, abstractmethod
from typing import Optional

from src.models.auth import User


class BaseAuthRepository(ABC):
    """Abstraction for user storage and federated identities."""

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    def username_exists(self, username: str) -> bool:
        ...

    @abstractmethod
    def create_user(self, username: str, email: str, password_hash: str) -> User:
        ...

    @abstractmethod
    def get_by_federated(self, provider: str, subject_id: str) -> Optional[User]:
        ...

    @abstractmethod
    def create_federated_user(
        self,
        provider: str,
        subject_id: str,
        username: str,
        email: str,
    ) -> User:
        ...