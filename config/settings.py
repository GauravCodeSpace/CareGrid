"""
CareGrid AI — Application Settings
====================================
Centralized configuration loader using python-dotenv.
All application settings are defined here for single-source-of-truth.

Usage:
    from config.settings import settings
    db_url = settings.DATABASE_URL
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file from project root ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


class _Settings:
    """
    Application settings container.
    Reads from environment variables with sensible defaults.
    """

    # ── Application ──
    APP_NAME: str = os.getenv("APP_NAME", "CareGrid AI")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_TAGLINE: str = "AI-Powered Healthcare Operations & Resource Management"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── Paths ──
    PROJECT_ROOT: Path = _PROJECT_ROOT
    ASSETS_DIR: Path = _PROJECT_ROOT / "assets"
    DATA_DIR: Path = _PROJECT_ROOT / "data"
    LOCALES_DIR: Path = _PROJECT_ROOT / "locales"

    # ── Database ──
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{_PROJECT_ROOT / 'data' / 'database.db'}"
    )

    # ── Security ──
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # ── Google Maps (Optional — falls back to Folium) ──
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    USE_GOOGLE_MAPS: bool = bool(GOOGLE_MAPS_API_KEY)

    # ── Translation ──
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    SUPPORTED_LANGUAGES: dict = {
        "English": "en",
        "हिन्दी": "hi",
    }

    # ── Streamlit Page Config ──
    PAGE_ICON: str = "🏥"
    PAGE_LAYOUT: str = "wide"

    # ── AI Thresholds ──
    LOW_STOCK_THRESHOLD_DAYS: int = 7  # Alert if stock runs out within N days
    CRITICAL_STOCK_THRESHOLD_DAYS: int = 3
    HIGH_ABSENTEEISM_THRESHOLD: float = 0.30  # 30% absence rate
    HIGH_BED_OCCUPANCY_THRESHOLD: float = 0.85  # 85% occupancy
    CRITICAL_BED_OCCUPANCY_THRESHOLD: float = 0.95

    # ── Risk Score Weights ──
    RISK_WEIGHT_STOCK: float = 0.30
    RISK_WEIGHT_ATTENDANCE: float = 0.25
    RISK_WEIGHT_BEDS: float = 0.25
    RISK_WEIGHT_DIAGNOSTICS: float = 0.20

    def __repr__(self) -> str:
        return (
            f"Settings(app={self.APP_NAME}, version={self.APP_VERSION}, "
            f"db={self.DATABASE_URL[:30]}...)"
        )


# ── Singleton instance ──
settings = _Settings()
