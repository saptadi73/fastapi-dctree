from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.datasets.models import Dataset


class DatasetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, dataset: Dataset) -> Dataset:
        self.session.add(dataset)
        await self.session.commit()
        await self.session.refresh(dataset)
        return dataset

    async def get_by_id(self, dataset_id) -> Dataset | None:
        result = await self.session.execute(select(Dataset).where(Dataset.id == dataset_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Dataset]:
        result = await self.session.execute(select(Dataset).order_by(Dataset.created_at.desc()))
        return list(result.scalars().all())

    async def update_profile(self, dataset: Dataset, profile_json: dict, status: str) -> Dataset:
        dataset.profile_json = profile_json
        dataset.status = status
        await self.session.commit()
        await self.session.refresh(dataset)
        return dataset

