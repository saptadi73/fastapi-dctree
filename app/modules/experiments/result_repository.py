from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.experiments.models import ClassMetric, ConfusionMatrixValue, FeatureImportance


class ExperimentResultRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_result_details(self, run_id, result_json: dict) -> None:
        labels = result_json["confusion_matrix"]["labels"]
        matrix = result_json["confusion_matrix"]["values"]

        for actual_label, row in zip(labels, matrix, strict=False):
            for predicted_label, value in zip(labels, row, strict=False):
                self.session.add(
                    ConfusionMatrixValue(
                        run_id=run_id,
                        actual_label=actual_label,
                        predicted_label=predicted_label,
                        value=int(value),
                    )
                )

        for metric in result_json["class_metrics"]:
            self.session.add(
                ClassMetric(
                    run_id=run_id,
                    class_label=metric["class_label"],
                    precision=metric["precision"],
                    recall=metric["recall"],
                    f1_score=metric["f1_score"],
                    support=metric["support"],
                )
            )

        for importance in result_json["feature_importance"]:
            self.session.add(
                FeatureImportance(
                    run_id=run_id,
                    feature_name=importance["feature"],
                    importance=importance["importance"],
                )
            )

        await self.session.commit()

    async def get_confusion_matrix(self, run_id) -> list[ConfusionMatrixValue]:
        result = await self.session.execute(
            select(ConfusionMatrixValue).where(ConfusionMatrixValue.run_id == run_id)
        )
        return list(result.scalars().all())

    async def get_class_metrics(self, run_id) -> list[ClassMetric]:
        result = await self.session.execute(
            select(ClassMetric).where(ClassMetric.run_id == run_id)
        )
        return list(result.scalars().all())

    async def get_feature_importances(self, run_id) -> list[FeatureImportance]:
        result = await self.session.execute(
            select(FeatureImportance).where(FeatureImportance.run_id == run_id)
        )
        return list(result.scalars().all())
