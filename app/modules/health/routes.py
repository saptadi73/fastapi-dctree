from fastapi import APIRouter, Request

from app.core.database import check_database_connection
from app.support.responses import success_response

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live(request: Request):
    return success_response({"status": "ok"}, request)


@router.get("/health/ready")
async def ready(request: Request):
    await check_database_connection()
    return success_response({"status": "ready", "database": "connected"}, request)


@router.get("/health/db")
async def database(request: Request):
    await check_database_connection()
    return success_response({"status": "ok", "database": "connected"}, request)
