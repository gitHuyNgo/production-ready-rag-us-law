"""
Ingestion worker service configuration.

Wraps the shared Settings from code_shared.core.config so ingestion-specific
settings can be added later without impacting other services.
"""
from code_shared.core.config import Settings as SharedSettings


class IngestionSettings(SharedSettings):
    """Settings specific to the ingestion-worker service."""

    # For now, this simply reuses the shared settings (OpenAI, Weaviate, Redis).
    # Ingestion-specific tuning knobs can be added here later.


settings = IngestionSettings()

