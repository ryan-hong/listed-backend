from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from listed_backend.database import get_db
from listed_backend.dependencies.auth import get_current_user
from listed_backend.models.list import List
from listed_backend.models.user import User
from listed_backend.schemas.list import ListCreate, ListResponse, ListUpdate
from listed_backend.services import lists as lists_service

router = APIRouter(prefix="/lists", tags=["lists"])


def _to_response(list_obj: List, entry_count: int) -> ListResponse:
    return ListResponse(
        id=list_obj.id,
        user_id=str(list_obj.user_id),
        name=list_obj.name,
        description=list_obj.description,
        emoji=list_obj.emoji,
        background_image_url=list_obj.background_image_url,
        sort_order=list_obj.sort_order,
        entry_count=entry_count,
        created_at=list_obj.created_at,
        updated_at=list_obj.updated_at,
    )


@router.get("", response_model=list[ListResponse])
async def get_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await lists_service.list_for_user(db, user)
    return [_to_response(list_obj, count) for list_obj, count in rows]


@router.get("/{list_id}", response_model=ListResponse)
async def get_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    list_obj = await lists_service.get_owned(db, user, list_id)
    count = await lists_service.entry_count_for(db, list_obj.id)
    return _to_response(list_obj, count)


@router.post("", response_model=ListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    body: ListCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    list_obj = await lists_service.create(db, user, body)
    return _to_response(list_obj, 0)


@router.patch("/{list_id}", response_model=ListResponse)
async def update_list(
    list_id: int,
    body: ListUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    list_obj = await lists_service.get_owned(db, user, list_id)
    list_obj = await lists_service.update(db, list_obj, body)
    count = await lists_service.entry_count_for(db, list_obj.id)
    return _to_response(list_obj, count)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    list_obj = await lists_service.get_owned(db, user, list_id)
    await lists_service.delete(db, list_obj)
