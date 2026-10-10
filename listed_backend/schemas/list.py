from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class Create(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    emoji: str | None = Field(None, max_length=20)
    background_image_url: str | None = None
    sort_order: int | None = None


class Update(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    emoji: str | None = Field(None, max_length=20)
    background_image_url: str | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "Update":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class Response(BaseModel):
    id: int
    user_id: str
    name: str
    description: str | None
    emoji: str | None
    background_image_url: str | None
    sort_order: int
    entry_count: int
    created_at: datetime
    updated_at: datetime
