"""Shared PostHog client configuration for the FastAPI application."""

import atexit
from functools import lru_cache
from typing import Optional

from posthog import Posthog
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostHogSettings(BaseSettings):
    """Optional PostHog configuration loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    posthog_project_token: Optional[str] = None
    posthog_host: Optional[str] = None


@lru_cache
def get_posthog_settings() -> PostHogSettings:
    """Return cached PostHog settings, allowing dependency overrides in tests."""
    return PostHogSettings()


posthog_client: Optional[Posthog] = None


def initialize_posthog() -> Optional[Posthog]:
    """Create the process-wide PostHog client when it is configured."""
    global posthog_client

    if posthog_client is not None:
        return posthog_client

    settings = get_posthog_settings()
    for variable, value in (
        ("POSTHOG_PROJECT_TOKEN", settings.posthog_project_token),
        ("POSTHOG_HOST", settings.posthog_host),
    ):
        if value:
            continue
        if settings.environment.lower() not in {"production", "prod"}:
            raise RuntimeError(
                f"{variable} variable required by PostHog is missing or un-configured, "
                f"this causes events to be silently missed. This error stops appearing "
                f"once {variable} is configured"
            )
        return None

    posthog_client = Posthog(
        settings.posthog_project_token,
        host=settings.posthog_host,
        enable_exception_autocapture=True,
        privacy_mode=True,
    )
    atexit.register(posthog_client.shutdown)
    return posthog_client


def flush_posthog() -> None:
    """Flush pending PostHog events during application shutdown."""
    if posthog_client is not None:
        posthog_client.flush()
