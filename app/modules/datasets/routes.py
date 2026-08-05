import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.datasets.schemas import DatasetRead
from app.modules.datasets.service import DatasetService
from app.support.responses import success_response

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/configuration-presets")
async def list_configuration_presets(request: Request, session: AsyncSession = Depends(get_db_session)):
    return success_response(DatasetService(session).list_configuration_presets(), request)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    project_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    dataset = await DatasetService(session).upload_dataset(project_id, file)
    return success_response(DatasetRead.model_validate(dataset).model_dump(), request)


@router.get("")
async def list_datasets(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    datasets = await DatasetService(session).list_datasets()
    data = [DatasetRead.model_validate(dataset).model_dump() for dataset in datasets]
    return success_response(data, request)


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    dataset = await DatasetService(session).get_dataset(dataset_id)
    return success_response(DatasetRead.model_validate(dataset).model_dump(), request)


@router.post("/{dataset_id}/profile")
async def profile_dataset(
    dataset_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    dataset = await DatasetService(session).profile_dataset(dataset_id)
    return success_response(DatasetRead.model_validate(dataset).model_dump(), request)


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    preview = await DatasetService(session).preview_dataset(dataset_id, limit=limit)
    return success_response(preview, request)


@router.get("/{dataset_id}/table")
async def get_dataset_table(
    dataset_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    normalized: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
):
    table = await DatasetService(session).get_dataset_table(
        dataset_id,
        page=page,
        page_size=page_size,
        normalized=normalized,
    )
    return success_response(table, request)


@router.post("/{dataset_id}/recommend-config")
async def recommend_dataset_config(
    dataset_id: uuid.UUID,
    request: Request,
    preset: Literal["indonesia", "india"] = Query(...),
    session: AsyncSession = Depends(get_db_session),
):
    recommendation = await DatasetService(session).recommend_dataset_config(dataset_id, preset=preset)
    return success_response(recommendation, request)


@router.get("/{dataset_id}/eda-visualization")
async def get_eda_visualization(
    dataset_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await DatasetService(session).get_eda_visualization(dataset_id)
    return success_response(data, request)


@router.get("/{dataset_id}/target-conversion-preview")
async def get_target_conversion_preview(
    dataset_id: uuid.UUID,
    request: Request,
    preset: Literal["indonesia", "india"] = Query(...),
    session: AsyncSession = Depends(get_db_session),
):
    data = await DatasetService(session).get_target_conversion_preview(dataset_id, preset=preset)
    return success_response(data, request)
