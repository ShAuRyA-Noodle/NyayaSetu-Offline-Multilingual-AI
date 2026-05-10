"""Centralized environment-driven settings for NyayaSetu.

Using pydantic-settings to enforce required vars in production and
provide typed access elsewhere via get_settings().
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: str = Field(default="development")

    # Database
    database_url: Optional[str] = Field(default=None)

    # LLM
    groq_api_key: Optional[str] = Field(default=None)
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # Voice
    sarvam_api_key: Optional[str] = Field(default=None)

    # Auth
    jwt_secret_key: Optional[str] = Field(default=None)
    nyayasetu_secret_key: Optional[str] = Field(default=None)  # legacy fallback
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_hours: int = Field(default=24)

    # CORS
    cors_origins: str = Field(default="")

    # Trusted proxies
    trusted_proxies: str = Field(default="*")

    # Captcha
    turnstile_secret_key: Optional[str] = Field(default=None)
    turnstile_site_key: Optional[str] = Field(default=None)

    # Observability
    sentry_dsn: Optional[str] = Field(default=None)
    log_level: str = Field(default="INFO")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)

    # Embeddings / RAG
    embedding_model: str = Field(
        default="paraphrase-multilingual-mpnet-base-v2"
    )
    faiss_index_path: str = Field(default="data/schemes_faiss.index")
    model_cache_dir: str = Field(default="models")

    # Ollama (dev only)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:14b-instruct")

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def effective_jwt_secret(self) -> Optional[str]:
        return self.jwt_secret_key or self.nyayasetu_secret_key

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production(self) -> List[str]:
        """Return a list of missing/invalid required vars. Empty list = OK."""
        missing: List[str] = []
        if not self.is_production:
            return missing
        if not self.effective_jwt_secret or self.effective_jwt_secret.startswith("change-this"):
            missing.append("JWT_SECRET_KEY")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        if not self.cors_origins:
            missing.append("CORS_ORIGINS")
        return missing


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
