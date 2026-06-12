"""
Config management — 12-Factor App (Factor III: Config).

Tất cả config đọc từ environment variables, KHÔNG hardcode.
Local dev: copy .env.example → .env
Production: set env vars trên Railway/Render dashboard.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # State (stateless design — mọi state nằm trong Redis)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    AGENT_API_KEY: str = "change-me-in-production"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Cost guard
    MONTHLY_BUDGET_USD: float = 10.0

    # LLM (Day 8 generation) — nếu để trống sẽ dùng Mock LLM (chạy offline)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # RAG (Day 8 retrieval)
    DATA_DIR: str = "data/standardized"
    TOP_K: int = 5
    HISTORY_MAX_TURNS: int = 10


settings = Settings()
