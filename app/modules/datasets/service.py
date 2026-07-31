from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ml.config_recommender import recommend_config
from app.ml.data_loader import load_dataframe_from_bytes
from app.ml.preprocessing import normalize_dataframe
from app.ml.schema_detector import build_dataset_profile
from app.modules.datasets.models import Dataset
from app.modules.datasets.repository import DatasetRepository
from app.support.checksums import sha256_bytes


class DatasetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = DatasetRepository(session)
        self.settings = get_settings()

    async def upload_dataset(self, project_id: str | None, upload_file: UploadFile) -> Dataset:
        content = await upload_file.read()
        dataset_id = uuid.uuid4()
        extension = Path(upload_file.filename or "dataset.csv").suffix or ".csv"
        storage_root = Path(self.settings.storage_dir)
        datasets_dir = storage_root / "datasets"
        datasets_dir.mkdir(parents=True, exist_ok=True)
        storage_path = datasets_dir / f"{dataset_id}{extension}"
        storage_path.write_bytes(content)

        dataset = Dataset(
            id=dataset_id,
            project_id=project_id,
            original_filename=upload_file.filename or "dataset",
            storage_path=str(storage_path),
            mime_type=upload_file.content_type,
            file_size=len(content),
            sha256=sha256_bytes(content),
            status="UPLOADED",
        )
        return await self.repository.create(dataset)

    async def get_dataset(self, dataset_id):
        dataset = await self.repository.get_by_id(dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found.")
        return dataset

    async def list_datasets(self) -> list[Dataset]:
        return await self.repository.list_all()

    async def profile_dataset(self, dataset_id):
        dataset = await self.get_dataset(dataset_id)
        dataframe = self._read_dataset_file(dataset.storage_path)
        profile = build_dataset_profile(dataframe)
        return await self.repository.update_profile(dataset, profile, "PROFILED")

    async def preview_dataset(self, dataset_id, limit: int = 20):
        dataset = await self.get_dataset(dataset_id)
        dataframe = self._read_dataset_file(dataset.storage_path)
        rows = json.loads(dataframe.head(limit).to_json(orient="records"))
        return {
            "dataset_id": str(dataset.id),
            "columns": dataframe.columns.tolist(),
            "rows": rows,
            "total_rows": int(len(dataframe)),
        }

    async def get_dataset_table(
        self,
        dataset_id,
        page: int = 1,
        page_size: int = 50,
        normalized: bool = False,
    ):
        dataset = await self.get_dataset(dataset_id)
        dataframe = (
            self._read_dataset_file(dataset.storage_path)
            if normalized
            else self._read_original_dataset_file(dataset.storage_path)
        )
        total_rows = int(len(dataframe))
        total_pages = (total_rows + page_size - 1) // page_size if total_rows else 0
        offset = (page - 1) * page_size
        page_rows = dataframe.iloc[offset : offset + page_size]
        rows = json.loads(page_rows.to_json(orient="records"))

        return {
            "dataset_id": str(dataset.id),
            "dataset_name": dataset.original_filename,
            "source": "normalized" if normalized else "original",
            "columns": dataframe.columns.tolist(),
            "rows": rows,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_rows": total_rows,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

    async def recommend_dataset_config(self, dataset_id):
        dataset = await self.get_dataset(dataset_id)
        dataframe = self._read_dataset_file(dataset.storage_path)
        profile = dataset.profile_json or build_dataset_profile(dataframe)
        if dataset.profile_json is None:
            await self.repository.update_profile(dataset, profile, "PROFILED")
        return recommend_config(dataframe, profile)

    async def get_eda_visualization(self, dataset_id):
        dataset = await self.get_dataset(dataset_id)
        dataframe = self._read_dataset_file(dataset.storage_path)
        profile = dataset.profile_json or build_dataset_profile(dataframe)
        if dataset.profile_json is None:
            await self.repository.update_profile(dataset, profile, "PROFILED")

        numeric_columns = [
            column for column in profile["columns"] if column.get("inferred_type") == "numeric"
        ]
        categorical_columns = [
            column for column in profile["columns"] if column.get("inferred_type") != "numeric"
        ]

        return {
            "dataset_id": str(dataset.id),
            "dataset_name": dataset.original_filename,
            "summary": profile["summary"],
            "charts": {
                "missing_ratio_by_column": [
                    {
                        "column": column["name"],
                        "missing_ratio": column["missing_ratio"],
                        "missing_count": column["missing_count"],
                    }
                    for column in profile["columns"]
                ],
                "unique_ratio_by_column": [
                    {
                        "column": column["name"],
                        "unique_ratio": column["unique_ratio"],
                        "unique_count": column["unique_count"],
                    }
                    for column in profile["columns"]
                ],
                "numeric_distributions": [
                    {
                        "column": column["name"],
                        "stats": column.get("stats", {}),
                    }
                    for column in numeric_columns
                ],
                "categorical_distributions": [
                    {
                        "column": column["name"],
                        "top_categories": column.get("top_categories", []),
                    }
                    for column in categorical_columns
                ],
            },
            "columns": profile["columns"],
        }

    async def get_target_conversion_preview(self, dataset_id):
        dataset = await self.get_dataset(dataset_id)
        dataframe = self._read_dataset_file(dataset.storage_path)
        profile = dataset.profile_json or build_dataset_profile(dataframe)
        if dataset.profile_json is None:
            await self.repository.update_profile(dataset, profile, "PROFILED")

        recommendation = recommend_config(dataframe, profile)
        target_column = recommendation["task"].get("target_column")
        positive_class = recommendation["task"].get("positive_class")
        target_distribution = []

        if target_column and target_column in dataframe.columns:
            counts = dataframe[target_column].astype("string").fillna("<NA>").value_counts()
            target_distribution = [
                {"label": label, "count": int(count)}
                for label, count in counts.items()
            ]

        return {
            "dataset_id": str(dataset.id),
            "target_column": target_column,
            "positive_class": positive_class,
            "task_type": recommendation["task"].get("type"),
            "target_distribution": target_distribution,
            "recommendations": recommendation.get("recommendations", []),
            "columns": recommendation.get("columns", []),
        }

    def _read_dataset_file(self, storage_path: str) -> pd.DataFrame:
        path = Path(storage_path)
        dataframe = load_dataframe_from_bytes(path.suffix.lower(), path.read_bytes())
        return normalize_dataframe(dataframe)

    def _read_original_dataset_file(self, storage_path: str) -> pd.DataFrame:
        path = Path(storage_path)
        return load_dataframe_from_bytes(path.suffix.lower(), path.read_bytes())
