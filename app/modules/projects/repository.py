from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectCreate


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: ProjectCreate) -> Project:
        project = Project(name=payload.name, description=payload.description)
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def list_all(self) -> list[Project]:
        result = await self.session.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

