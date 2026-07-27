"""Runtime configuration. Everything tunable lives here and nowhere else."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models_data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- app ---
    app_name: str = "ThumbIQ"
    version: str = "1.0.0"
    debug: bool = False

    # --- CORS ---
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- rate limits (per client IP) ---
    rate_limit_thumbnails_per_min: int = 30
    rate_limit_analyze_per_min: int = 10
    rate_limit_ai_per_hour: int = 40
    rate_limit_batch_per_hour: int = 6
    rate_limit_download_per_min: int = 60

    # --- caching ---
    cache_ttl_seconds: int = 3600
    cache_max_resolutions: int = 512
    cache_max_images: int = 128
    cache_max_renditions: int = 1024
    cache_max_analyses: int = 256

    # --- fetching ---
    max_image_bytes: int = 20 * 1024 * 1024
    max_html_bytes: int = 2 * 1024 * 1024
    connect_timeout: float = 15.0
    total_timeout: float = 30.0
    allow_private_hosts: bool = False  # tests flip this; never true in production

    # --- analysis ---
    analysis_concurrency: int = 4
    batch_concurrency: int = 4
    batch_max_items: int = 24
    ocr_min_confidence: float = 55.0
    tesseract_cmd: str = ""  # explicit path when tesseract isn't on PATH

    # --- AI ---
    ai_enabled: bool = True
    ai_model: str = "claude-opus-4-8"
    ai_max_tokens: int = 8000
    ai_effort: str = "high"
    ai_timeout: float = 120.0
    anthropic_api_key: str = ""

    # Published Opus 4.8 pricing, USD per million tokens. Used only for the running
    # cost estimate on /api/health — never for a billing decision.
    ai_input_cost_per_mtok: float = 5.0
    ai_output_cost_per_mtok: float = 25.0
    ai_cache_read_cost_per_mtok: float = 0.5
    ai_cache_write_cost_per_mtok: float = 6.25

    @field_validator("ai_effort")
    @classmethod
    def _valid_effort(cls, value: str) -> str:
        allowed = {"low", "medium", "high", "xhigh", "max"}
        if value not in allowed:
            raise ValueError(f"ai_effort must be one of {sorted(allowed)}")
        return value

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def models_dir(self) -> Path:
        return BASE_DIR / "models"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
