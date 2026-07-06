"""Central configuration for YushaCyber.

All configuration lives here as classes consumed by the application
factory via ``app.config.from_object``. Paths are built with pathlib —
no hardcoded absolute paths — and secrets come from the environment
(loaded from a project-root .env file by python-dotenv).
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Project root = the directory containing this file.
BASE_DIR = Path(__file__).resolve().parent

# Flask's conventional writable folder for local data (gitignored).
INSTANCE_DIR = BASE_DIR / "instance"

load_dotenv(BASE_DIR / ".env")


def _bool_env(name: str, default: str = "false") -> bool:
    """Read an environment variable as a boolean flag."""
    return os.environ.get(name, default).strip().lower() == "true"


class Config:
    """Base configuration shared by every environment."""

    # ------------------------------------------------------------------
    # Secrets — never hardcoded. An ephemeral key keeps development
    # working, at the cost of sessions resetting on restart; the factory
    # logs a warning when this fallback is used.
    # ------------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SECRET_KEY_IS_EPHEMERAL = SECRET_KEY is None
    if SECRET_KEY_IS_EPHEMERAL:
        SECRET_KEY = secrets.token_hex(32)

    # ------------------------------------------------------------------
    # Database — SQLite file inside instance/ for development; override
    # with DATABASE_URL (e.g. a PostgreSQL URI) in production.
    # ------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + (INSTANCE_DIR / "yushacyber.db").as_posix(),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------------------
    # Session / cookie hardening
    # ------------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE")
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE


class DevelopmentConfig(Config):
    """Local development settings."""

    DEBUG = True


class ProductionConfig(Config):
    """Production settings — secure cookies expected behind HTTPS."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


# Selected via the APP_ENV environment variable (default: development).
CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config() -> type[Config]:
    """Return the config class for the current APP_ENV."""
    env = os.environ.get("APP_ENV", "development").strip().lower()
    return CONFIG_BY_NAME.get(env, DevelopmentConfig)
