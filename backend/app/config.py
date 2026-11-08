"""Application settings. Everything comes from environment variables (or a .env file).

Nothing in here is ever changed at runtime through the API.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/riskwise"

    # --- Auth ---------------------------------------------------------------
    # "dev": HS256 tokens minted by /api/v1/dev/token (never enable in prod).
    # "oidc": RS256/ES256 tokens from any OIDC issuer (Supabase Auth, Azure AD, Okta...).
    auth_mode: Literal["dev", "oidc"] = "dev"
    dev_jwt_secret: str = "dev-only-change-me"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""

    # --- Secrets at rest ----------------------------------------------------
    # Fernet key (urlsafe base64, 32 bytes). Encrypts BYOK LLM keys and integration tokens.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # --- Storage ------------------------------------------------------------
    storage_backend: Literal["local"] = "local"
    storage_local_dir: str = "./data/uploads"
    max_upload_mb: int = 15

    # --- Analysis limits (cost and abuse control) ---------------------------
    max_clauses_per_contract: int = 400
    max_llm_clauses_per_run: int = 60
    llm_timeout_seconds: float = 60.0

    # --- Jobs ---------------------------------------------------------------
    # Shared secret for the scheduler (e.g. GitHub Actions cron) to call /api/v1/jobs/*.
    job_token: str = ""

    # --- Email (SMTP works with any provider and with self-hosted relays) ----
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "RISKWISE AI <no-reply@localhost>"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
