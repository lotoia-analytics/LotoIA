"""Application settings for LotoIA."""
from __future__ import annotations
import os


class _Settings:
    app_name: str = "LotoIA API"
    app_env: str = os.getenv("APP_ENV", "production")


settings = _Settings()
