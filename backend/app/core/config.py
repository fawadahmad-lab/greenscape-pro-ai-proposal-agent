"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Greenscape Pro proposal copilot backend."""

    app_name: str = "Greenscape Pro AI Proposal Copilot"
    database_url: str
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_extract_max_attempts: int = 2
    resend_api_key: str | None = None
    from_email: str | None = None
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS value into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
