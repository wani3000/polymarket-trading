from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    database_path: str = Field(default="data/api.sqlite3")
    session_ttl_hours: int = Field(default=24 * 7)

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)

    model_config = {"env_prefix": "API_", "env_file": ".env", "extra": "ignore"}


settings = ApiSettings()
