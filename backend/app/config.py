from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "fixtures"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    ai_explanations_enabled: bool = True
    max_upload_bytes: int = 10 * 1024 * 1024
    preview_row_limit: int = 50
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:3001"
    database_url: str = ""
    static_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
