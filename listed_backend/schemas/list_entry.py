from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from listed_backend.models.list_entry import EntryType
from listed_backend.schemas.entry_metadata import trimmed_text, validate_metadata
from listed_backend.schemas.validation import raise_field_error


Position = Annotated[StrictInt, Field(ge=-2_147_483_648, le=2_147_483_647)]


def normalized_metadata(entry_type: EntryType, meta: dict | None) -> dict:
    try:
        return validate_metadata(entry_type, meta)
    except ValidationError as exc:
        errors = exc.errors(include_url=False)
        for error in errors:
            error["loc"] = ("meta", *error["loc"])
        raise ValidationError.from_exception_data("ListEntry", errors) from None
    except ValueError as exc:
        raise_field_error("ListEntry", ("meta",), str(exc), meta)


class EntryLogFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(None, strict=True)
    rating: Annotated[StrictFloat, Field(ge=1, le=10, allow_inf_nan=False)] | None = None
    occurred_at: AwareDatetime | None = None

    @field_validator("note")
    @classmethod
    def nonblank_note(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("note must not be blank")
        return value

    @field_validator("rating")
    @classmethod
    def rating_increment(cls, value):
        if value is not None and Decimal(str(value)) % Decimal("0.1") != 0:
            raise ValueError("rating must use increments of 0.1")
        return value


class EntryLogCreate(EntryLogFields):
    @model_validator(mode="after")
    def nonempty_log(self):
        if self.note is None and self.rating is None and self.occurred_at is None:
            raise ValueError("a log requires a note, rating, or experience date")
        return self


class EntryLogUpdate(EntryLogFields):
    @model_validator(mode="after")
    def update_fields(self):
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class ListEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_type: EntryType
    title: trimmed_text(500)
    position: Position | None = None
    is_favourited: StrictBool = False
    external_source: trimmed_text(50) | None = None
    external_id: trimmed_text(255) | None = None
    meta: dict | None = None
    log: EntryLogCreate

    @model_validator(mode="after")
    def metadata(self):
        self.meta = normalized_metadata(self.entry_type, self.meta)
        return self


class ListEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_type: EntryType | None = None
    title: trimmed_text(500) | None = None
    position: Position | None = None
    is_favourited: StrictBool | None = None
    external_source: trimmed_text(50) | None = None
    external_id: trimmed_text(255) | None = None
    meta: dict | None = None

    @model_validator(mode="after")
    def update_fields(self):
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        for field in ("entry_type", "title", "position", "is_favourited"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise_field_error("ListEntry", (field,), "must not be null")
        return self


class EntryMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    log_id: int
    url: str
    media_type: str
    position: int
    created_at: datetime


class EntryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    note: str | None
    rating: float | None
    occurred_at: datetime | None
    created_at: datetime
    updated_at: datetime
    media: list[EntryMediaResponse]


class ListEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int
    entry_type: EntryType
    title: str
    position: int
    is_favourited: bool
    log_count: int
    external_source: str | None
    external_id: str | None
    meta: dict
    created_at: datetime
    updated_at: datetime
    logs: list[EntryLogResponse]

    @field_validator("meta", mode="before")
    @classmethod
    def metadata_object(cls, value):
        return {} if value is None else value
