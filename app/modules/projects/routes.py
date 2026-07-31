from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.projects.schemas import ProjectCreate, ProjectRead
from app.modules.projects.service import ProjectService
from app.support.responses import success_response

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    project = await ProjectService(session).create_project(payload)
    return success_response(ProjectRead.model_validate(project).model_dump(), request)


@router.get("")
async def list_projects(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    projects = await ProjectService(session).list_projects()
    data = [ProjectRead.model_validate(project).model_dump() for project in projects]
    return success_response(data, request)

