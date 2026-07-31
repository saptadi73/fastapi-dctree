from __future__ import annotations

from typing import Any

import pandas as pd


IDENTIFIER_HINTS = ("id", "uuid", "nim", "kode", "nomor", "no_", "nik")
TARGET_HINTS = ("target", "label", "class", "status", "hasil", "ipk", "lulus")


def recommend_config(dataframe: pd.DataFrame, profile: dict[str, Any]) -> dict[str, Any]:
    column_profiles = profile["columns"]
    target_candidate = _pick_target_candidate(column_profiles)
    columns = []
    recommendations = []

    for column_profile in column_profiles:
        name = column_profile["name"]
        inferred_type = column_profile["inferred_type"]
        unique_ratio = column_profile["unique_ratio"]
        unique_count = column_profile["unique_count"]

        role = "feature"
        enabled = True
        confidence = 0.65
        reasons = [f"inferred_type={inferred_type}"]

        if _looks_identifier(name, unique_ratio):
            role = "identifier"
            enabled = False
            confidence = 0.98
            reasons = ["unique_ratio high", "column name matches identifier pattern"]
        elif target_candidate and target_candidate["name"] == name:
            role = "target"
            enabled = True
            confidence = target_candidate["confidence"]
            reasons = target_candidate["reasons"]

        column_config: dict[str, Any] = {
            "name": name,
            "data_type": inferred_type,
            "role": role,
            "enabled": enabled,
        }
        if inferred_type == "ordinal":
            categories = _extract_ordinal_categories(dataframe[name])
            if categories:
                column_config["encoding"] = "ordinal"
                column_config["categories"] = categories
        elif inferred_type == "categorical":
            column_config["encoding"] = "one_hot"

        columns.append(column_config)
        recommendations.append(
            {
                "column": name,
                "recommended_role": role,
                "confidence": confidence,
                "reasons": reasons,
                "requires_confirmation": role == "target",
            }
        )

    target_column = target_candidate["name"] if target_candidate else ""
    positive_class = None
    if target_column:
        target_values = dataframe[target_column].dropna().astype(str).unique().tolist()
        if len(target_values) == 2:
            positive_class = sorted(target_values)[-1]

    return {
        "schema_version": "1.0",
        "task": {
            "type": "classification",
            "target_column": target_column,
            "positive_class": positive_class,
        },
        "preprocessing": {
            "mode": "strict",
            "collapse_rare_study_programs": True,
            "simplify_social_media_platforms": True,
            "normalize_binary_labels": True,
            "normalize_duration_buckets": True,
        },
        "columns": columns,
        "split": {
            "method": "train_test",
            "test_size": 0.2,
            "stratify": True,
            "random_state": 42,
        },
        "model": {
            "algorithm": "decision_tree_classifier",
            "criterion": "gini",
            "splitter": "best",
            "max_depth": 4,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42,
        },
        "recommendations": recommendations,
    }


def _pick_target_candidate(column_profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = []
    for column_profile in column_profiles:
        name = column_profile["name"]
        unique_count = column_profile["unique_count"]
        unique_ratio = column_profile["unique_ratio"]
        if 1 < unique_count <= 10 and unique_ratio < 0.5:
            confidence = 0.7
            reasons = ["low cardinality suitable for classification target"]
            if any(hint in name.lower() for hint in TARGET_HINTS):
                confidence = 0.9
                reasons.append("column name matches target pattern")
            candidates.append(
                {"name": name, "confidence": confidence, "reasons": reasons}
            )
    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return candidates[0] if candidates else None


def _looks_identifier(name: str, unique_ratio: float) -> bool:
    lowered = name.lower()
    return unique_ratio >= 0.95 or any(hint in lowered for hint in IDENTIFIER_HINTS)


def _extract_ordinal_categories(series: pd.Series) -> list[Any]:
    non_null = series.dropna()
    numeric_cast = pd.to_numeric(non_null, errors="coerce")
    if numeric_cast.notna().all():
        return sorted(numeric_cast.unique().tolist())
    return list(dict.fromkeys(non_null.astype(str).tolist()))
