import json

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.data_loader import load_dataframe_from_bytes
from app.ml.preprocessing import normalize_dataframe
from app.ml.trainer import train_decision_tree
from app.modules.experiments.repository import ExperimentRepository
from app.modules.experiments.result_repository import ExperimentResultRepository
from app.modules.experiments.schemas import DecisionTreeConfig


class ExperimentService:
    def __init__(self, session: AsyncSession):
        self.repository = ExperimentRepository(session)

    async def train_from_upload(
        self,
        run_name: str,
        config_raw: str,
        upload_file: UploadFile,
    ):
        config = DecisionTreeConfig.model_validate(json.loads(config_raw))
        content = await upload_file.read()
        dataframe = load_dataframe_from_bytes(
            self._extract_extension(upload_file.filename or ""),
            content,
        )
        dataframe = normalize_dataframe(dataframe, config.preprocessing)
        result = train_decision_tree(dataframe, config)
        return await self.repository.create(run_name, config.model_dump(), result)

    async def list_runs(self):
        return await self.repository.list_all()

    async def get_run(self, run_id):
        run = await self.repository.get_by_id(run_id)
        if run is None:
            raise ValueError("Experiment run not found.")
        return run

    async def get_confusion_matrix(self, run_id):
        run = await self.get_run(run_id)
        rows = await ExperimentResultRepository(self.repository.session).get_confusion_matrix(run.id)
        return self._build_confusion_matrix_payload(run, rows)

    async def get_metrics(self, run_id):
        run = await self.get_run(run_id)
        result_repository = ExperimentResultRepository(self.repository.session)
        class_metrics = await result_repository.get_class_metrics(run.id)
        confusion_matrix = await result_repository.get_confusion_matrix(run.id)
        metrics = self._build_aggregate_metrics(
            run.result_json.get("metrics", {}),
            class_metrics,
            confusion_matrix,
        )
        return {
            "run_id": str(run.id),
            "metrics": metrics,
            "class_metrics": [
                {
                    "class_label": row.class_label,
                    "precision": row.precision,
                    "recall": row.recall,
                    "f1_score": row.f1_score,
                    "support": row.support,
                }
                for row in class_metrics
            ],
        }

    async def get_feature_importance(self, run_id):
        run = await self.get_run(run_id)
        rows = await ExperimentResultRepository(self.repository.session).get_feature_importances(run.id)
        transformed_importance = [
            {
                "feature_name": row.feature_name,
                "importance": row.importance,
                "value": row.importance,
            }
            for row in rows
        ]
        original_importance = self._build_original_feature_importance(
            transformed_importance,
            run.config_json.get("columns", []),
        )
        return {
            "run_id": str(run.id),
            "feature_importance": transformed_importance,
            "transformed_feature_importance": transformed_importance,
            "original_feature_importance": original_importance,
        }

    async def get_preprocessing_summary(self, run_id):
        run = await self.get_run(run_id)
        summary = run.result_json.get("preprocessing_summary")
        if summary is None:
            raise ValueError("Preprocessing summary not available for this run.")
        return {
            "run_id": str(run.id),
            **summary,
        }

    async def get_tree_visualization(self, run_id):
        run = await self.get_run(run_id)
        visualization = run.result_json.get("tree_visualization")
        if visualization is None:
            raise ValueError("Tree visualization data not available for this run.")
        return {
            "run_id": str(run.id),
            **visualization,
        }

    async def get_workflow_visualization(self, run_id):
        run = await self.get_run(run_id)
        result = run.result_json
        config = run.config_json
        result_repository = ExperimentResultRepository(self.repository.session)
        confusion_matrix = self._build_confusion_matrix_payload(
            run,
            await result_repository.get_confusion_matrix(run.id),
        )

        return {
            "run_id": str(run.id),
            "run_name": run.run_name,
            "steps": [
                {
                    "step_number": 1,
                    "code": "eda",
                    "title": "Exploratory Data Analysis (EDA)",
                    "status": "not_available",
                    "visualization_type": "dataset-profile",
                    "endpoint": None,
                    "notes": "Profiling dataset tersedia di modul dataset, tetapi tidak tersimpan pada experiment run ini.",
                },
                {
                    "step_number": 2,
                    "code": "preprocessing",
                    "title": "Preprocessing Data",
                    "status": "available" if result.get("preprocessing_summary") else "not_available",
                    "visualization_type": "summary-cards-and-table",
                    "endpoint": f"/api/v1/experiments/runs/{run.id}/preprocessing-summary",
                    "data": result.get("preprocessing_summary"),
                },
                {
                    "step_number": 3,
                    "code": "target-conversion",
                    "title": "Konversi CGPA Menjadi Kategori",
                    "status": "configured" if config.get("task", {}).get("target_column") else "not_available",
                    "visualization_type": "config-summary",
                    "endpoint": None,
                    "data": {
                        "target_column": config.get("task", {}).get("target_column"),
                        "positive_class": config.get("task", {}).get("positive_class"),
                    },
                },
                {
                    "step_number": 4,
                    "code": "model-training",
                    "title": "Pembangunan Model Decision Tree",
                    "status": "available",
                    "visualization_type": "summary-cards",
                    "endpoint": f"/api/v1/experiments/runs/{run.id}",
                    "data": {
                        "status": run.status,
                        "split": result.get("dataset_split"),
                        "model": config.get("model"),
                    },
                },
                {
                    "step_number": 5,
                    "code": "confusion-matrix",
                    "title": "Confusion Matrix",
                    "status": "available",
                    "visualization_type": "heatmap",
                    "endpoint": f"/api/v1/experiments/runs/{run.id}/confusion-matrix",
                    "data": confusion_matrix,
                },
                {
                    "step_number": 6,
                    "code": "metrics",
                    "title": "Accuracy, Precision, Recall, dan F1-Score",
                    "status": "available",
                    "visualization_type": "metric-cards-and-table",
                    "endpoint": f"/api/v1/experiments/runs/{run.id}/metrics",
                    "data": {
                        "metrics": result.get("metrics"),
                        "class_metrics": result.get("class_metrics"),
                    },
                },
                {
                    "step_number": 7,
                    "code": "decision-tree-visualization",
                    "title": "Visualisasi Pohon Keputusan",
                    "status": "available" if result.get("tree_visualization") else "not_available",
                    "visualization_type": "node-link-diagram",
                    "endpoint": f"/api/v1/experiments/runs/{run.id}/tree-visualization",
                    "data": result.get("tree_visualization"),
                },
            ],
        }

    def _extract_extension(self, filename: str) -> str:
        return f".{filename.split('.')[-1].lower()}" if "." in filename else ""

    def _build_aggregate_metrics(self, stored_metrics, class_metrics, confusion_matrix):
        metrics = dict(stored_metrics or {})

        total_support = sum(row.support for row in class_metrics)
        if total_support:
            metrics.setdefault(
                "precision",
                sum(row.precision * row.support for row in class_metrics) / total_support,
            )
            metrics.setdefault(
                "recall",
                sum(row.recall * row.support for row in class_metrics) / total_support,
            )
            metrics.setdefault(
                "f1_score",
                sum(row.f1_score * row.support for row in class_metrics) / total_support,
            )

        total_predictions = sum(row.value for row in confusion_matrix)
        if total_predictions:
            correct_predictions = sum(
                row.value
                for row in confusion_matrix
                if row.actual_label == row.predicted_label
            )
            metrics.setdefault("accuracy", correct_predictions / total_predictions)

        if "f1_score" in metrics:
            metrics.setdefault("f1", metrics["f1_score"])

        return metrics

    def _build_confusion_matrix_payload(self, run, rows):
        labels = run.result_json.get("confusion_matrix", {}).get("labels")
        if not labels:
            labels = sorted({row.actual_label for row in rows} | {row.predicted_label for row in rows})

        values_by_label = {
            (row.actual_label, row.predicted_label): row.value
            for row in rows
        }

        return {
            "run_id": str(run.id),
            "labels": labels,
            "values": [
                [
                    values_by_label.get((actual_label, predicted_label), 0)
                    for predicted_label in labels
                ]
                for actual_label in labels
            ],
            "entries": [
                {
                    "actual_label": row.actual_label,
                    "predicted_label": row.predicted_label,
                    "value": row.value,
                }
                for row in rows
            ],
            "orientation": {"rows": "actual", "columns": "predicted"},
        }

    def _build_original_feature_importance(self, transformed_importance, config_columns):
        importance_by_feature: dict[str, float] = {}
        for row in transformed_importance:
            original_feature = self._extract_original_feature_name(
                row["feature_name"],
                config_columns,
            )
            importance_by_feature[original_feature] = (
                importance_by_feature.get(original_feature, 0.0) + row["importance"]
            )

        total_importance = sum(importance_by_feature.values())
        return [
            {
                "feature_name": feature_name,
                "importance": importance,
                "value": importance,
                "percentage": (importance / total_importance * 100.0) if total_importance else 0.0,
            }
            for feature_name, importance in sorted(
                importance_by_feature.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    def _extract_original_feature_name(self, transformed_feature_name: str, config_columns) -> str:
        if "__" not in transformed_feature_name:
            return transformed_feature_name

        _, feature_name = transformed_feature_name.split("__", 1)

        original_features = {
            column.get("name")
            for column in config_columns
            if column.get("role") == "feature"
        }
        matching_features = [
            original_feature
            for original_feature in original_features
            if original_feature and feature_name.startswith(f"{original_feature}_")
        ]
        if matching_features:
            return max(matching_features, key=len)

        return feature_name
