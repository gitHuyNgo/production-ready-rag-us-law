"""External identity provider integrations (e.g., Google OIDC)."""

from .google import google_auth, init_google

__all__ = ["google_auth", "init_google"]

