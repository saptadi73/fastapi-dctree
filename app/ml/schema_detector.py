from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype


def build_dataset_profile(dataframe: pd.DataFrame) -> dict[str, Any]:
    columns = []
    total_rows = len(dataframe)
    duplicate_rows = int(dataframe.duplicated().sum())

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        inferred_type = _infer_column_type(series)
        column_profile: dict[str, Any] = {
            "name": column_name,
            "inferred_type": inferred_type,
            "missing_count": missing_count,
            "missing_ratio": _ratio(missing_count, total_rows),
            "unique_count": unique_count,
            "unique_ratio": _ratio(unique_count, total_rows),
        }

        if inferred_type == "numeric":
            numeric_series = pd.to_numeric(series, errors="coerce").dropna()
            column_profile["stats"] = {
                "min": _as_float(numeric_series.min()),
                "max": _as_float(numeric_series.max()),
                "mean": _as_float(numeric_series.mean()),
                "median": _as_float(numeric_series.median()),
            }
        else:
            top_categories = series.astype("string").fillna("<NA>").value_counts().head(10)
            column_profile["top_categories"] = [
                {"value": value, "count": int(count)} for value, count in top_categories.items()
            ]

        columns.append(column_profile)

    return {
        "summary": {
            "rows": total_rows,
            "columns": len(dataframe.columns),
            "duplicate_rows": duplicate_rows,
            "missing_cells": int(dataframe.isna().sum().sum()),
        },
        "columns": columns,
    }


def _infer_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "categorical"
    if is_numeric_dtype(series):
        return "numeric"
    numeric_cast = pd.to_numeric(non_null, errors="coerce")
    if numeric_cast.notna().mean() > 0.9:
        return "numeric"
    unique_count = non_null.nunique()
    if unique_count <= 12 and _looks_ordinal(non_null):
        return "ordinal"
    return "categorical"


def _looks_ordinal(series: pd.Series) -> bool:
    numeric_cast = pd.to_numeric(series, errors="coerce")
    if numeric_cast.notna().all():
        return True
    normalized = {str(value).strip().lower() for value in series.unique().tolist()}
    ordinal_vocab = {"low", "medium", "high", "sangat rendah", "rendah", "sedang", "tinggi"}
    return normalized.issubset(ordinal_vocab)


def _ratio(value: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(value / total, 4)


def _as_float(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)

