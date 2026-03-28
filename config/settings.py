"""
Central configuration: load config/.env (then repo .env) and typed getters.
All tunables for scripts should be documented in config/.env.example.
"""
from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE_CONFIG = _REPO_ROOT / "config" / ".env"
ENV_FILE_ROOT = _REPO_ROOT / ".env"


def load_env() -> Path | None:
    """Load environment variables from file. Returns path loaded or None."""
    from dotenv import load_dotenv

    if ENV_FILE_CONFIG.is_file():
        load_dotenv(ENV_FILE_CONFIG)
        return ENV_FILE_CONFIG
    if ENV_FILE_ROOT.is_file():
        load_dotenv(ENV_FILE_ROOT)
        return ENV_FILE_ROOT
    return None


def get_str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


def get_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return default
    return int(v)


def get_float(key: str, default: float) -> float:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return default
    return float(v)


def get_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def get_path(key: str, default: str) -> Path:
    v = os.getenv(key)
    if v is None or not str(v).strip():
        s = default
    else:
        s = str(v).strip()
    p = Path(s)
    if not p.is_absolute():
        return (_REPO_ROOT / p).resolve()
    return p


def get_int_optional(key: str) -> int | None:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return None
    return int(v)


def get_path_optional(key: str) -> Path | None:
    v = os.getenv(key)
    if v is None or not str(v).strip():
        return None
    p = Path(str(v).strip())
    if not p.is_absolute():
        return (_REPO_ROOT / p).resolve()
    return p
