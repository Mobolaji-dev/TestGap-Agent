from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TESTGAP_", env_file=".env", extra="ignore")

    repository_path: Path | None = Field(default=None)
    repository_workspace_root: Path = Field(default=Path("/tmp/testgap-workspaces"))
    repository_clone_timeout_seconds: int = Field(default=120, ge=10, le=600)
    repository_max_size_mb: int = Field(default=200, ge=10, le=2000)
    run_timeout_seconds: int = Field(default=90, ge=5, le=600)
    run_database_path: Path = Field(default=Path(".runs/testgap.sqlite3"))
    litellm_api_key: SecretStr | None = Field(default=None, validation_alias="LITELLM_API_KEY")
    litellm_base_url: str = Field(
        default="https://litellm.vision.aivar.app/v1",
        validation_alias="LITELLM_BASE_URL",
    )
    litellm_model: str = Field(default="claude-haiku", validation_alias="LITELLM_MODEL")
    neatlogs_api_key: SecretStr | None = Field(default=None, validation_alias="NEATLOGS_API_KEY")
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
