from datetime import datetime

from pydantic import BaseModel, ConfigDict

from listed_backend.schemas.entry_metadata import trimmed_text


class TagWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: trimmed_text(64)


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
