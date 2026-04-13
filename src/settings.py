"""Runtime settings shared across the application and scripts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.agent.grounding import GroundingConfig, ScoreAggregation

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
        enable_decoding=False,
    )

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    admin_api_token: str | None = Field(
        default=None,
        alias="ADMIN_API_TOKEN",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

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

    conversation_db_path: Path | None = Field(
        default=None,
        alias="CONVERSATION_DB_PATH",
    )
    conversation_history_max_turns: int = Field(
        default=10,
        alias="CONVERSATION_HISTORY_MAX_TURNS",
    )
    grounding_min_top_score: float = Field(
        default=0.3,
        alias="GROUNDING_MIN_TOP_SCORE",
    )
    grounding_min_results: int = Field(
        default=1,
        alias="GROUNDING_MIN_RESULTS",
    )
    grounding_score_aggregation: ScoreAggregation = Field(
        default="max",
        alias="GROUNDING_SCORE_AGGREGATION",
    )
    grounding_expected_top_k: int = Field(
        default=5,
        alias="GROUNDING_EXPECTED_TOP_K",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None or value == "":
            return list(_DEFAULT_CORS_ORIGINS)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: str | None) -> str:
        normalized = (value or "INFO").strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(
                f"LOG_LEVEL must be one of {sorted(allowed)}, got {normalized!r}"
            )
        return normalized

    @property
    def effective_conversation_db_path(self) -> Path:
        return self.conversation_db_path or (self.data_dir / "conversations.db")

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

    @property
    def grounding_config(self) -> GroundingConfig:
        return GroundingConfig(
            min_top_score=self.grounding_min_top_score,
            min_results=self.grounding_min_results,
            score_aggregation=self.grounding_score_aggregation,
            expected_top_k=self.grounding_expected_top_k,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
