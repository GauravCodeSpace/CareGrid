"""
CareGrid AI — Translation Utility
====================================
Multi-language support with JSON-based translation files and
on-the-fly dynamic translation via Google Translate.

Usage:
    from utils.translator import t, get_current_language, translate_dynamic

    label = t("dashboard.title")
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import streamlit as st

from config.settings import settings

logger = logging.getLogger(__name__)

# ============================================================
# TRANSLATION FILE LOADING
# ============================================================

_translations: dict[str, dict] = {}


def _load_translations() -> None:
    """
    Load all JSON locale files from the ``locales/`` directory.
    Called lazily on the first ``t()`` invocation.
    """
    global _translations

    locales_dir: Path = settings.LOCALES_DIR
    if not locales_dir.is_dir():
        logger.warning("Locales directory not found: %s", locales_dir)
        return

    for json_file in locales_dir.glob("*.json"):
        lang_code = json_file.stem  # e.g. "en", "hi"
        try:
            with open(json_file, "r", encoding="utf-8") as fh:
                _translations[lang_code] = json.load(fh)
            logger.debug("Loaded locale: %s (%d keys)", lang_code, len(_translations[lang_code]))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load locale '%s': %s", lang_code, exc)


def _ensure_loaded() -> None:
    """Ensure translation files have been loaded at least once."""
    if not _translations:
        _load_translations()


# ============================================================
# CORE TRANSLATION FUNCTION
# ============================================================

def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Look up a translation key for the current language.

    Supports dot-separated nested keys, e.g. ``"dashboard.title"``.
    Falls back to English, then to the default string, then to the raw key string.

    Args:
        key: Dot-separated translation key.
        default: Optional default string to return if key is not found.

    Returns:
        Translated string, default, or the key itself if not found.
    """
    _ensure_loaded()

    lang = get_current_language()
    value = _resolve_key(_translations.get(lang, {}), key)

    # Fallback to English
    if value is None and lang != "en":
        value = _resolve_key(_translations.get("en", {}), key)

    if value is not None:
        return value
    return default if default is not None else key


def _resolve_key(data: dict, key: str) -> Optional[str]:
    """
    Resolve a dot-separated key against a nested dictionary.

    Args:
        data: Translation dictionary.
        key: Dot-separated key.

    Returns:
        The value string, or None if not found.
    """
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current if isinstance(current, str) else None


# ============================================================
# DYNAMIC TRANSLATION (Google Translate)
# ============================================================

@lru_cache(maxsize=1024)
def _cached_translate(text: str, target_lang: str) -> str:
    """Cache wrapper around Google Translator to avoid repeated API calls."""
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return translated or text
    except Exception as exc:
        logger.warning("Dynamic translation failed for '%s': %s", text[:40], exc)
        return text


def translate_dynamic(text: str, target_lang: str) -> str:
    """
    Translate arbitrary text to the target language using Google Translate.

    Results are cached (LRU, 1 024 entries) to minimise API calls.

    Args:
        text: Source text to translate.
        target_lang: ISO 639-1 language code (e.g. "hi", "en").

    Returns:
        Translated text, or original text on failure.
    """
    if not text or not text.strip():
        return text
    if target_lang == "en":
        return text
    return _cached_translate(text, target_lang)


# ============================================================
# LANGUAGE HELPERS
# ============================================================

def get_current_language() -> str:
    """
    Get the current language code from Streamlit session state.

    Returns:
        Language code (e.g. "en" or "hi"). Defaults to ``settings.DEFAULT_LANGUAGE``.
    """
    try:
        return st.session_state.get("language", settings.DEFAULT_LANGUAGE)
    except Exception:
        # May be called outside Streamlit context (e.g. tests, scripts)
        return settings.DEFAULT_LANGUAGE
