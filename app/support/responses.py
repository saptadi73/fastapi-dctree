from datetime import datetime, timezone
from typing import Any

from fastapi import Request


def success_response(data: Any, request: Request) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "meta": {
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

