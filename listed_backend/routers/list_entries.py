from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from listed_backend.database import get_db
from listed_backend.dependencies.auth import get_current_user
from listed_backend.models.user import User
from listed_backend.schemas.list_entry import (
    EntryLogCreate,
    EntryLogResponse,
    EntryLogUpdate,
    ListEntryCreate,
    ListEntryResponse,
    ListEntryUpdate,
)
from listed_backend.services import list_entries as entries_service

router = APIRouter(prefix="/lists/{list_id}/entries", tags=["entries"])


@router.post("", response_model=ListEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    list_id: int,
    body: ListEntryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await entries_service.create(db, user, list_id, body)


@router.get("/{entry_id}", response_model=ListEntryResponse)
async def get_entry(
    list_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await entries_service.get_owned(db, user, list_id, entry_id)


@router.patch("/{entry_id}", response_model=ListEntryResponse)
async def update_entry(
    list_id: int,
    entry_id: int,
    body: ListEntryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await entries_service.update(db, user, list_id, entry_id, body)
    return await entries_service.get_owned(db, user, list_id, entry_id)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    list_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await entries_service.get_owned(db, user, list_id, entry_id)
    await entries_service.delete(db, entry)


@router.post(
    "/{entry_id}/logs",
    response_model=EntryLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_entry_log(
    list_id: int,
    entry_id: int,
    body: EntryLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await entries_service.get_owned(db, user, list_id, entry_id)
    return await entries_service.add_log(db, entry, body)


@router.patch("/{entry_id}/logs/{log_id}", response_model=EntryLogResponse)
async def update_entry_log(
    list_id: int,
    entry_id: int,
    log_id: int,
    body: EntryLogUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await entries_service.update_log(db, user, list_id, entry_id, log_id, body)
