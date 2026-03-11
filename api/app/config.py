from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    database_path: str = Field(default="data/api.sqlite3")
    session_ttl_hours: int = Field(default=24 * 7)
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_prefix": "API_", "env_file": ".env", "extra": "ignore"}


settings = ApiSettings()
