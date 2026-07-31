from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.repository import ProjectRepository
from app.modules.projects.schemas import ProjectCreate


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.repository = ProjectRepository(session)

    async def create_project(self, payload: ProjectCreate):
        return await self.repository.create(payload)

    async def list_projects(self):
        return await self.repository.list_all()

