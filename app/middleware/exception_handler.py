from datetime import datetime, timezone

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": exc.errors(),
                },
                "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": exc.errors(),
                },
                "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled request error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                },
                "meta": {
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )
