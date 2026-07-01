from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SQLITE_URL = f"sqlite:///{(_REPOSITORY_ROOT / 'data' / 'app.db').as_posix()}"


class Settings(BaseSettings):
    """Runtime settings loaded from process environment and the repository .env."""

    model_config = SettingsConfigDict(
        env_file=str(_REPOSITORY_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_debug: bool = False
    database_url: str = _DEFAULT_SQLITE_URL
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized, non-empty browser origins for CORS middleware."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings()
