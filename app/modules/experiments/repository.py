from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.experiments.models import ExperimentRun
from app.modules.experiments.result_repository import ExperimentResultRepository


class ExperimentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, run_name: str, config_json: dict, result_json: dict) -> ExperimentRun:
        run = ExperimentRun(
            run_name=run_name,
            status="completed",
            config_json=config_json,
            result_json=result_json,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        await ExperimentResultRepository(self.session).save_result_details(run.id, result_json)
        return run

    async def list_all(self) -> list[ExperimentRun]:
        result = await self.session.execute(
            select(ExperimentRun).order_by(ExperimentRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, run_id) -> ExperimentRun | None:
        result = await self.session.execute(select(ExperimentRun).where(ExperimentRun.id == run_id))
        return result.scalar_one_or_none()
