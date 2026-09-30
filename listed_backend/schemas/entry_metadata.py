"""Entry metadata schemas shared by API mutations and provider imports."""

import json
import math
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    RootModel,
    StrictFloat,
    StrictInt,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

from listed_backend.models.list_entry import EntryType
from listed_backend.schemas.validation import raise_field_error


def _trim(value):
    return value.strip() if isinstance(value, str) else value


def trimmed_text(max_length: int):
    """A strict, nonblank string type with surrounding whitespace removed."""
    return Annotated[
        str,
        StringConstraints(strict=True, min_length=1, max_length=max_length),
        BeforeValidator(_trim),
    ]


Text = trimmed_text(255)
LongText = trimmed_text(10_000)
Year = Annotated[StrictInt, Field(ge=1, le=9999)]
PositiveInteger = Annotated[StrictInt, Field(ge=1, le=2_147_483_647)]
NonNegativeInteger = Annotated[StrictInt, Field(ge=0, le=2_147_483_647)]


def _deduplicate(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


Labels = Annotated[
    list[trimmed_text(64)], Field(max_length=50), AfterValidator(_deduplicate)
]
Names = Annotated[list[Text], Field(max_length=50), AfterValidator(_deduplicate)]


def _url(value: str) -> str:
    # Validate syntax without replacing the user's URL with a canonical spelling.
    parts = urlsplit(value)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("must be an absolute http or https URL with a host")
    TypeAdapter(HttpUrl).validate_python(value)
    return value


URL = Annotated[trimmed_text(2048), AfterValidator(_url)]


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("must be an ISO 8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


Timestamp = Annotated[str, Field(strict=True), AfterValidator(_timestamp)]


def _iana_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("must be a valid IANA time zone identifier") from None
    return value


TimeZone = Annotated[trimmed_text(128), AfterValidator(_iana_timezone)]


def _isbn(value: str) -> str:
    value = value.replace(" ", "").replace("-", "").upper()
    if len(value) == 10:
        if (
            all(c in "0123456789" for c in value[:9])
            and value[-1] in "0123456789X"
            and sum(
                (10 - i) * (10 if c == "X" else int(c))
                for i, c in enumerate(value)
            ) % 11 == 0
        ):
            return value
    elif len(value) == 13 and all(c in "0123456789" for c in value):
        checksum = sum(
            int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(value)
        )
        if checksum % 10 == 0:
            return value
    raise ValueError("must be a valid ISBN-10 or ISBN-13")


ISBN = Annotated[str, Field(strict=True), AfterValidator(_isbn)]


def _field_error(model: BaseModel, field: str, message: str):
    raise_field_error(type(model).__name__, (field,), message, getattr(model, field))


class SharedMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: LongText | None = None
    tags: Labels | None = None
    website_url: URL | None = None
    image_url: URL | None = None


class LocationMetadata(SharedMetadata):
    address: trimmed_text(512) | None = None
    city: trimmed_text(128) | None = None
    region: trimmed_text(128) | None = None
    country: trimmed_text(128) | None = None
    postal_code: trimmed_text(32) | None = None
    latitude: Annotated[StrictFloat, Field(ge=-90, le=90, allow_inf_nan=False)] | None = None
    longitude: Annotated[StrictFloat, Field(ge=-180, le=180, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            missing = "latitude" if self.latitude is None else "longitude"
            _field_error(self, missing, "latitude and longitude must be supplied together")
        return self


class RestaurantMetadata(LocationMetadata):
    cuisines: Labels | None = None
    price_range: Annotated[StrictInt, Field(ge=1, le=4)] | None = None
    neighborhood: trimmed_text(128) | None = None
    phone: trimmed_text(64) | None = None
    menu_url: URL | None = None


class MovieMetadata(SharedMetadata):
    directors: Names | None = None
    release_year: Year | None = None
    genres: Labels | None = None
    runtime_minutes: PositiveInteger | None = None
    cast: Names | None = None
    streaming_services: Labels | None = None


class PlaceMetadata(LocationMetadata):
    place_category: trimmed_text(64) | None = None
    best_season: Text | None = None


class MealMetadata(SharedMetadata):
    cuisine: Text | None = None
    ingredients: Annotated[list[trimmed_text(500)], Field(max_length=100)] | None = None
    recipe: trimmed_text(20_000) | None = None
    recipe_url: URL | None = None
    servings: PositiveInteger | None = None
    prep_minutes: NonNegativeInteger | None = None
    cook_minutes: NonNegativeInteger | None = None


class BookMetadata(SharedMetadata):
    authors: Names | None = None
    publication_year: Year | None = None
    genres: Labels | None = None
    publisher: Text | None = None
    isbn: ISBN | None = None
    page_count: PositiveInteger | None = None
    edition: Text | None = None


class TVShowMetadata(SharedMetadata):
    creators: Names | None = None
    release_year: Year | None = None
    end_year: Year | None = None
    genres: Labels | None = None
    networks: Labels | None = None
    season_count: PositiveInteger | None = None
    episode_runtime_minutes: PositiveInteger | None = None
    streaming_services: Labels | None = None

    @model_validator(mode="after")
    def year_order(self):
        if (
            self.release_year is not None
            and self.end_year is not None
            and self.end_year < self.release_year
        ):
            _field_error(self, "end_year", "must be greater than or equal to release_year")
        return self


class VideoGameMetadata(SharedMetadata):
    developers: Names | None = None
    publishers: Names | None = None
    release_year: Year | None = None
    genres: Labels | None = None
    platforms: Labels | None = None


class PodcastMetadata(SharedMetadata):
    hosts: Names | None = None
    publisher: Text | None = None
    genres: Labels | None = None
    language: trimmed_text(64) | None = None
    feed_url: URL | None = None


class EventMetadata(LocationMetadata):
    event_category: trimmed_text(64) | None = None
    starts_at: Timestamp | None = None
    ends_at: Timestamp | None = None
    timezone: TimeZone | None = None
    venue: Text | None = None
    performers: Names | None = None
    organizer: Text | None = None
    ticket_url: URL | None = None

    @model_validator(mode="after")
    def time_order(self):
        if self.ends_at is not None:
            if self.starts_at is None:
                _field_error(self, "starts_at", "is required when ends_at is supplied")
            if datetime.fromisoformat(self.ends_at) < datetime.fromisoformat(self.starts_at):
                _field_error(self, "ends_at", "must be greater than or equal to starts_at")
        return self


class CustomMetadata(RootModel[dict]):
    pass


METADATA_SCHEMAS = {
    EntryType.RESTAURANT: RestaurantMetadata,
    EntryType.MOVIE: MovieMetadata,
    EntryType.PLACE: PlaceMetadata,
    EntryType.MEAL: MealMetadata,
    EntryType.BOOK: BookMetadata,
    EntryType.TV_SHOW: TVShowMetadata,
    EntryType.VIDEO_GAME: VideoGameMetadata,
    EntryType.PODCAST: PodcastMetadata,
    EntryType.EVENT: EventMetadata,
    EntryType.CUSTOM: CustomMetadata,
}


def _check_json(value, path=()):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _check_json(item, (*path, index))
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for key, item in value.items():
            _check_json(item, (*path, key))
        return
    raise_field_error(
        "EntryMetadata",
        path,
        "must be a valid JSON value with finite numbers and string object keys",
        value,
    )


def validate_metadata(entry_type: EntryType | str, meta: dict | None) -> dict:
    """Normalize metadata; ValidationError locations are relative to meta."""
    entry_type = TypeAdapter(EntryType).validate_python(entry_type)
    if meta is None:
        meta = {}
    if type(meta) is not dict:
        raise ValueError("meta must be a JSON object")
    _check_json(meta)
    validated = METADATA_SCHEMAS[entry_type].model_validate(meta)
    if entry_type == EntryType.CUSTOM:
        normalized = validated.model_dump()
    else:
        normalized = validated.model_dump(exclude_none=True)
    try:
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, UnicodeEncodeError):
        raise ValueError("meta must be valid UTF-8 JSON") from None
    if len(encoded) > 64 * 1024:
        raise ValueError("meta must not exceed 64 KiB of compact UTF-8 JSON")
    return normalized
