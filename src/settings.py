"""Runtime settings shared across the application and scripts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    cors_origins: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_CORS_ORIGINS),
        alias="CORS_ORIGINS",
    )

    raw_corpus_dir: Path = Field(
        default=Path("dataset/itc2026_ai_corpus"),
        alias="RAW_CORPUS_DIR",
    )
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    auto_build_artifacts: bool = Field(
        default=True,
        alias="AUTO_BUILD_ARTIFACTS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None or value == "":
            return list(_DEFAULT_CORS_ORIGINS)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def cleaned_dir(self) -> Path:
        return self.data_dir / "cleaned"

    @property
    def metadata_path(self) -> Path:
        return self.data_dir / "metadata.json"

    @property
    def filter_report_path(self) -> Path:
        return self.data_dir / "filter_report.json"

    @property
    def chunk_manifest_path(self) -> Path:
        return self.data_dir / "chunks.jsonl"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "indexes"

    @property
    def whoosh_dir(self) -> Path:
        return self.index_dir / "whoosh"

    @property
    def index_manifest_path(self) -> Path:
        return self.index_dir / "manifest.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
