import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None = None
    original_filename: str
    storage_path: str
    mime_type: str | None = None
    file_size: int
    sha256: str
    status: str
    profile_json: dict[str, Any] | None = None
    created_at: datetime

