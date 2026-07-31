from __future__ import annotations

import re

import pandas as pd

from app.modules.experiments.schemas import DecisionTreePreprocessingConfig


YES_VALUES = {"ya", "iya", "y", "yes"}
NO_VALUES = {"tidak", "tdk", "no", "n"}

SOCIAL_MEDIA_CANONICAL = {
    "tiktok": "TikTok",
    "tik tok": "TikTok",
    "tiktokk": "TikTok",
    "instagram": "Instagram",
    "ig": "Instagram",
    "facebook": "Facebook",
    "twitter": "Twitter",
    "twitter/x": "Twitter",
    "x": "Twitter",
    "telegram": "Telegram",
    "line": "Line",
    "whatsapp": "WhatsApp",
    "whats app": "WhatsApp",
    "whatsaap": "WhatsApp",
    "whathsapl": "WhatsApp",
    "wa": "WhatsApp",
}

STUDY_PROGRAM_CANONICAL = {
    "teknik informatika": "Teknik Informatika",
    "informatika": "Informatika",
    "sistem informasi": "Sistem Informasi",
    "teknik sipil": "Teknik Sipil",
    "teknik elektro": "Teknik Elektro",
    "teknik arsitektur": "Teknik Arsitektur",
    "manajemen": "Manajemen",
    "akuntansi": "Akuntansi",
    "farmasi": "Farmasi",
    "hukum": "Hukum",
    "psikologi": "Psikologi",
    "pgsd": "PGSD",
    "pg paud": "PG PAUD",
    "pg-paud": "PG PAUD",
    "pendidikan fisika": "Pendidikan Fisika",
    "pendidikan matematika": "Pendidikan Matematika",
    "kesehatan masyarakat": "Kesehatan Masyarakat",
    "ilmu komunikasi": "Ilmu Komunikasi",
    "ilmu pemerintahan": "Ilmu Pemerintahan",
    "bioteknologi": "Bioteknologi",
    "matematika": "Matematika",
    "statistika": "Statistika",
    "ekonomi pembangunan": "Ekonomi Pembangunan",
    "administrasi bisnis": "Administrasi Bisnis",
    "bimbingan konseling": "Bimbingan Konseling",
    "bimbingan dan konseling": "Bimbingan Konseling",
}

COMMON_STUDY_PROGRAMS = {
    "Teknik Informatika",
    "Farmasi",
    "Teknik Sipil",
    "Manajemen",
    "Pendidikan Fisika",
    "Hukum",
    "Kesehatan Masyarakat",
    "Psikologi",
    "Bioteknologi",
    "Akuntansi",
    "PG PAUD",
    "Administrasi Bisnis",
    "Bimbingan Konseling",
    "Matematika",
    "Ilmu Komunikasi",
    "PGSD",
}


def normalize_dataframe(
    dataframe: pd.DataFrame,
    config: DecisionTreePreprocessingConfig | None = None,
) -> pd.DataFrame:
    config = config or DecisionTreePreprocessingConfig()
    normalized = dataframe.copy()

    for column_name in normalized.columns:
        series = normalized[column_name]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            normalized[column_name] = _normalize_text_series(column_name, series, config)

    return normalized


def _normalize_text_series(
    column_name: str,
    series: pd.Series,
    config: DecisionTreePreprocessingConfig,
) -> pd.Series:
    normalized = series.map(_clean_text_value)
    if config.mode == "raw":
        return normalized

    lowered_name = column_name.strip().lower()
    if (
        ("program studi" in lowered_name or "jurusan" in lowered_name)
        and config.collapse_rare_study_programs
    ):
        return normalized.map(_normalize_study_program)
    if "platform media sosial" in lowered_name and config.simplify_social_media_platforms:
        return normalized.map(_normalize_platform_value)
    if "menggunakan media sosial dalam sehari" in lowered_name and config.normalize_duration_buckets:
        return normalized.map(_normalize_social_media_duration)
    if "tidur dalam sehari" in lowered_name and config.normalize_duration_buckets:
        return normalized.map(_normalize_sleep_duration)
    if config.normalize_binary_labels and normalized.dropna().map(_looks_binary_label).all():
        return normalized.map(_normalize_binary_label)

    return normalized


def _clean_text_value(value):
    if pd.isna(value):
        return value
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def _normalize_binary_label(value):
    if value is None or pd.isna(value):
        return value
    lowered = str(value).strip().lower()
    if lowered in YES_VALUES:
        return "Ya"
    if lowered in NO_VALUES:
        return "Tidak"
    return str(value).strip().title()


def _looks_binary_label(value) -> bool:
    if value is None or pd.isna(value):
        return True
    lowered = str(value).strip().lower()
    return lowered in YES_VALUES or lowered in NO_VALUES


def _normalize_study_program(value):
    if value is None or pd.isna(value):
        return value
    text = str(value).strip()
    collapsed = re.sub(r"\s+", " ", text).lower()
    cleaned = collapsed.replace(".", "").replace("/", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    canonical = STUDY_PROGRAM_CANONICAL.get(cleaned, " ".join(word.capitalize() for word in cleaned.split()))
    if canonical not in COMMON_STUDY_PROGRAMS:
        return "Lainnya"
    return canonical


def _normalize_platform_value(value):
    if value is None or pd.isna(value):
        return value

    raw_text = str(value).strip()
    lowered = raw_text.lower()
    separators_pattern = r",|/| dan | & |\+"
    parts = [part.strip() for part in re.split(separators_pattern, lowered) if part.strip()]

    canonical_parts: list[str] = []
    for part in parts:
        canonical = SOCIAL_MEDIA_CANONICAL.get(part)
        if canonical is None:
            if "tiktok" in part or "tik tok" in part:
                canonical = "TikTok"
            elif "instagram" in part or part == "ig":
                canonical = "Instagram"
            elif "whatsapp" in part or part == "wa":
                canonical = "WhatsApp"
            elif "twitter" in part or part == "x":
                canonical = "Twitter"
            elif "facebook" in part:
                canonical = "Facebook"
            elif "telegram" in part:
                canonical = "Telegram"
            elif "line" in part:
                canonical = "Line"

        if canonical and canonical not in canonical_parts:
            canonical_parts.append(canonical)

    if canonical_parts:
        return canonical_parts[0]

    return " ".join(word.capitalize() for word in raw_text.split())


def _normalize_social_media_duration(value):
    if value is None or pd.isna(value):
        return value

    lowered = str(value).strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)

    if "kurang dari 6 jam" in lowered:
        return "Kurang dari 6 jam"
    if "lebih dari 6 jam" in lowered:
        return "Lebih dari 6 jam"
    if "lebih dari 2 jam" in lowered:
        return "2 sampai 6 jam"

    return str(value).strip().title()


def _normalize_sleep_duration(value):
    if value is None or pd.isna(value):
        return value

    lowered = str(value).strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)

    if "kurang dari 6 jam" in lowered:
        return "Kurang dari 6 jam"
    if "kurang dari 8 jam" in lowered:
        return "6 sampai 8 jam"
    if "lebih dari 8 jam" in lowered:
        return "Lebih dari 8 jam"

    return str(value).strip().title()
