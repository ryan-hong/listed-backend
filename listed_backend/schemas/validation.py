"""Shared field errors and JSON-safe HTTP validation responses."""

import math

from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.requests import Request


def raise_field_error(title: str, location: tuple, message: str, value=None):
    raise ValidationError.from_exception_data(
        title,
        [
            {
                "type": "value_error",
                "loc": location,
                "input": value,
                "ctx": {"error": ValueError(message)},
            }
        ],
    )


def as_request_validation_error(exc: ValidationError) -> RequestValidationError:
    errors = exc.errors(include_url=False)
    for error in errors:
        error["loc"] = ("body", *error["loc"])
    return RequestValidationError(errors)


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


async def json_safe_validation_handler(request: Request, exc: RequestValidationError):
    # Error inputs may contain NaN/Infinity even though those values were rejected.
    errors = _json_safe(jsonable_encoder(exc.errors()))
    safe_exc = RequestValidationError(errors, body=exc.body)
    return await request_validation_exception_handler(request, safe_exc)
