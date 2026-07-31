import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.experiments.schemas import ExperimentRunRead
from app.modules.experiments.service import ExperimentService
from app.support.responses import success_response

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/runs/upload-train", status_code=status.HTTP_201_CREATED)
async def upload_and_train(
    request: Request,
    run_name: str = Form(...),
    config_json: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
):
    run = await ExperimentService(session).train_from_upload(run_name, config_json, file)
    return success_response(ExperimentRunRead.model_validate(run).model_dump(), request)


@router.get("/runs")
async def list_runs(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    runs = await ExperimentService(session).list_runs()
    data = [ExperimentRunRead.model_validate(run).model_dump() for run in runs]
    return success_response(data, request)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    run = await ExperimentService(session).get_run(run_id)
    return success_response(ExperimentRunRead.model_validate(run).model_dump(), request)


@router.get("/runs/{run_id}/confusion-matrix")
async def get_confusion_matrix(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await ExperimentService(session).get_confusion_matrix(run_id)
    return success_response(data, request)


@router.get("/runs/{run_id}/metrics")
async def get_metrics(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await ExperimentService(session).get_metrics(run_id)
    return success_response(data, request)


@router.get("/runs/{run_id}/feature-importance")
async def get_feature_importance(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await ExperimentService(session).get_feature_importance(run_id)
    return success_response(data, request)


@router.get("/runs/{run_id}/preprocessing-summary")
async def get_preprocessing_summary(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await ExperimentService(session).get_preprocessing_summary(run_id)
    return success_response(data, request)


@router.get("/runs/{run_id}/tree-visualization")
async def get_tree_visualization(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await ExperimentService(session).get_tree_visualization(run_id)
    return success_response(data, request)


@router.get("/runs/{run_id}/workflow-visualization")
async def get_workflow_visualization(
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    data = await ExperimentService(session).get_workflow_visualization(run_id)
    return success_response(data, request)
