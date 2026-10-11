from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TESTGAP_", env_file=".env", extra="ignore")

    repository_path: Path | None = Field(default=None)
    repository_workspace_root: Path = Field(default=Path("/tmp/testgap-workspaces"))
    repository_clone_timeout_seconds: int = Field(default=120, ge=10, le=600)
    repository_max_size_mb: int = Field(default=200, ge=10, le=2000)
    run_timeout_seconds: int = Field(default=90, ge=5, le=600)
    run_database_path: Path = Field(default=Path(".runs/testgap.sqlite3"))
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("TESTGAP_DATABASE_URL", "DATABASE_URL"),
    )
    litellm_api_key: SecretStr | None = Field(default=None, validation_alias="LITELLM_API_KEY")
    litellm_base_url: str = Field(
        default="https://litellm.vision.aivar.app/v1",
        validation_alias="LITELLM_BASE_URL",
    )
    litellm_model: str = Field(default="claude-haiku", validation_alias="LITELLM_MODEL")
    neatlogs_api_key: SecretStr | None = Field(default=None, validation_alias="NEATLOGS_API_KEY")
    neatlogs_endpoint: str = Field(
        default="https://ingest.neatlogs.com",
        validation_alias="NEATLOGS_ENDPOINT",
    )
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://testgap.pxxl.click",
            "https://testgap-agent.pxxl.click",
            "https://test-gap-agent.vercel.app",
        ],
        validation_alias=AliasChoices("TESTGAP_CORS_ORIGINS", "CORS_ORIGINS"),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
