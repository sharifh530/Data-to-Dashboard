from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DTD_", env_file=".env", extra="ignore")
    environment: str = "local"
    database_url: SecretStr | None = None
    app_origin: str = "http://127.0.0.1:8000"
    inspection_image: str | None = None

    @model_validator(mode="after")
    def local_origin(self) -> "Settings":
        if self.inspection_image:
            import re

            if not re.fullmatch(r"sha256:[a-f0-9]{64}", self.inspection_image):
                raise ValueError("Inspection image must be a pinned local image ID")
        value = urlsplit(self.app_origin)
        if value.scheme not in {"http", "https"} or value.hostname not in {
            "localhost",
            "127.0.0.1",
        }:
            raise ValueError("Local authentication requires a loopback application origin")
        if value.path or value.query or value.fragment or value.username or value.password:
            raise ValueError("Application origin must contain only scheme, host, and optional port")
        return self


ROOT = Path(__file__).resolve().parents[4]
