from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.database import Base, engine
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.modules.datasets.routes import router as dataset_router
from app.modules.experiments.routes import router as experiment_router
from app.modules.health.routes import router as health_router
from app.modules.projects.routes import router as project_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(project_router, prefix=settings.api_v1_prefix)
app.include_router(dataset_router, prefix=settings.api_v1_prefix)
app.include_router(experiment_router, prefix=settings.api_v1_prefix)
