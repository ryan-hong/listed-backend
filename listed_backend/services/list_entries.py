from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from listed_backend.models.list import List
from listed_backend.models.list_entry import EntryLog, ListEntry
from listed_backend.models.user import User
from listed_backend.schemas.list_entry import (
    EntryLogCreate,
    EntryLogUpdate,
    ListEntryCreate,
    ListEntryUpdate,
    normalized_metadata,
)
from listed_backend.schemas.validation import as_request_validation_error, raise_field_error


async def get_owned(
    db: AsyncSession,
    user: User,
    list_id: int,
    entry_id: int,
) -> ListEntry:
    result = await db.execute(
        select(ListEntry)
        .join(List, List.id == ListEntry.list_id)
        .where(
            ListEntry.id == entry_id,
            ListEntry.list_id == list_id,
            List.user_id == user.id,
        )
        .options(selectinload(ListEntry.logs).selectinload(EntryLog.media))
        .execution_options(populate_existing=True)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


def _raise_integrity_error(exc: IntegrityError):
    error = exc.orig
    while error is not None:
        name = getattr(error, "constraint_name", None)
        if name is None:
            name = getattr(getattr(error, "diag", None), "constraint_name", None)
        if name == "ux_list_entries_list_external":
            raise HTTPException(
                status_code=409,
                detail="This item already exists in the list. Add a log to the existing entry instead.",
            ) from None
        error = error.__cause__
    raise exc


async def _commit(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        _raise_integrity_error(exc)


async def create(
    db: AsyncSession,
    user: User,
    list_id: int,
    payload: ListEntryCreate,
) -> ListEntry:
    # Serialize appends within a list, and verify ownership before inserting.
    result = await db.execute(
        select(List)
        .where(List.id == list_id, List.user_id == user.id)
        .with_for_update()
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="List not found")
    position = payload.position
    if position is None:
        result = await db.execute(
            select(func.coalesce(func.max(ListEntry.position), -1))
            .where(ListEntry.list_id == list_id)
        )
        position = result.scalar_one() + 1
        if position > 2_147_483_647:
            raise HTTPException(status_code=409, detail="No append position is available")
    # The nested log becomes a related row; position was calculated above.
    fields = payload.model_dump(exclude={"log", "position"})
    fields["entry_type"] = payload.entry_type.value
    entry = ListEntry(
        **fields,
        list_id=list_id,
        position=position,
        log_count=1,
        logs=[EntryLog(**payload.log.model_dump(), media=[])],
    )
    db.add(entry)
    await _commit(db)
    return await get_owned(db, user, list_id, entry.id)


async def update(
    db: AsyncSession,
    user: User,
    list_id: int,
    entry_id: int,
    payload: ListEntryUpdate,
) -> ListEntry:
    result = await db.execute(
        select(ListEntry)
        .join(List, List.id == ListEntry.list_id)
        .where(
            ListEntry.id == entry_id,
            ListEntry.list_id == list_id,
            List.user_id == user.id,
        )
        # Read the current type and metadata under a lock before validating edits.
        .with_for_update(of=ListEntry)
        .execution_options(populate_existing=True)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    fields = payload.model_dump(exclude_unset=True)
    entry_type = payload.entry_type or entry.entry_type
    try:
        if entry_type != entry.entry_type and "meta" not in fields:
            raise_field_error(
                "ListEntry", ("meta",), "meta must be provided when changing entry_type"
            )
        # Validate the effective type and metadata before changing any fields.
        meta = normalized_metadata(entry_type, fields.get("meta", entry.meta))
    except ValidationError as exc:
        raise as_request_validation_error(exc) from None
    if "meta" in fields:
        fields["meta"] = meta
    if "entry_type" in fields:
        fields["entry_type"] = payload.entry_type.value
    try:
        await db.execute(
            sql_update(ListEntry).where(ListEntry.id == entry.id).values(**fields)
        )
    except IntegrityError as exc:
        await db.rollback()
        _raise_integrity_error(exc)
    await _commit(db)
    return entry


async def delete(db: AsyncSession, entry: ListEntry) -> None:
    await db.delete(entry)
    await db.commit()


async def add_log(
    db: AsyncSession,
    entry: ListEntry,
    payload: EntryLogCreate,
) -> EntryLog:
    log = EntryLog(entry_id=entry.id, **payload.model_dump(), media=[])
    db.add(log)
    # Increment in SQL so concurrent log requests cannot lose increments.
    await db.execute(
        sql_update(ListEntry)
        .where(ListEntry.id == entry.id)
        .values(log_count=ListEntry.log_count + 1)
    )
    await _commit(db)
    # Refresh generated columns without expiring media and triggering async lazy IO.
    await db.refresh(log, attribute_names=["id", "created_at", "updated_at"])
    return log


async def update_log(
    db: AsyncSession,
    user: User,
    list_id: int,
    entry_id: int,
    log_id: int,
    payload: EntryLogUpdate,
) -> EntryLog:
    result = await db.execute(
        select(EntryLog)
        .join(ListEntry, ListEntry.id == EntryLog.entry_id)
        .join(List, List.id == ListEntry.list_id)
        .where(
            EntryLog.id == log_id,
            ListEntry.id == entry_id,
            List.id == list_id,
            List.user_id == user.id,
        )
        .options(selectinload(EntryLog.media))
        # Serialize edits so two requests cannot each clear the other's last content.
        .with_for_update(of=EntryLog)
        .execution_options(populate_existing=True)
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    fields = payload.model_dump(exclude_unset=True)
    note = fields.get("note", log.note)
    rating = fields.get("rating", log.rating)
    occurred_at = fields.get("occurred_at", log.occurred_at)
    if note is None and rating is None and occurred_at is None and not log.media:
        try:
            raise_field_error(
                "EntryLog",
                (),
                "a log must retain a note, rating, experience date, or media",
                fields,
            )
        except ValidationError as exc:
            raise as_request_validation_error(exc) from None
    await db.execute(
        sql_update(EntryLog).where(EntryLog.id == log.id).values(**fields)
    )
    await _commit(db)
    await db.refresh(
        log, attribute_names=["note", "rating", "occurred_at", "updated_at"]
    )
    return log
