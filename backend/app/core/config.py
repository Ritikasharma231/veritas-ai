from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VERITAS AI"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"

    database_url: str = f"sqlite:///{BASE_DIR / 'veritas.db'}"

    api_keys: str = ""
    max_text_length: int = 50000
    max_fetch_bytes: int = 2_000_000
    fetch_timeout_seconds: float = 15.0

    model_path: str = ""
    model_hf_id: str = "hamzab/roberta-fake-news-classification"
    model_max_length: int = 512
    model_labels: str = "Fake,Real"
    force_cpu: bool = False

    rate_limit_per_minute: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def label_list(self) -> list[str]:
        return [l.strip() for l in self.model_labels.split(",") if l.strip()]

    @property
    def reports_dir(self) -> Path:
        return BASE_DIR.parent / "ml" / "reports"

    @property
    def checkpoints_dir(self) -> Path:
        return BASE_DIR.parent / "ml" / "checkpoints"


@lru_cache
def get_settings() -> Settings:
    return Settings()
