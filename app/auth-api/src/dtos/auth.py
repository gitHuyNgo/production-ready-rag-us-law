"""Auth-related DTOs (API request/response models)."""

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    """User data returned by API (no password)."""

    username: str
    email: str

