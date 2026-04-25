from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listed_backend.models.list import List
from listed_backend.models.list_entry import ListEntry
from listed_backend.models.user import User
from listed_backend.schemas.list import ListCreate, ListUpdate


async def list_for_user(db: AsyncSession, user: User) -> list[tuple[List, int]]:
    stmt = (
        select(List, func.count(ListEntry.id))
        .outerjoin(ListEntry, ListEntry.list_id == List.id)
        .where(List.user_id == user.id)
        .group_by(List.id)
        .order_by(List.sort_order.asc(), List.id.asc())
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get_owned(db: AsyncSession, user: User, list_id: int) -> List:
    result = await db.execute(
        select(List).where(List.id == list_id, List.user_id == user.id)
    )
    list_obj = result.scalar_one_or_none()
    if list_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="List not found"
        )
    return list_obj


async def entry_count_for(db: AsyncSession, list_id: int) -> int:
    result = await db.execute(
        select(func.count(ListEntry.id)).where(ListEntry.list_id == list_id)
    )
    return result.scalar_one()


async def create(db: AsyncSession, user: User, payload: ListCreate) -> List:
    if payload.sort_order is None:
        max_result = await db.execute(
            select(func.coalesce(func.max(List.sort_order), -1)).where(
                List.user_id == user.id
            )
        )
        sort_order = max_result.scalar_one() + 1
    else:
        sort_order = payload.sort_order

    list_obj = List(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        emoji=payload.emoji,
        background_image_url=payload.background_image_url,
        sort_order=sort_order,
    )
    db.add(list_obj)
    await db.commit()
    await db.refresh(list_obj)
    return list_obj


async def update(db: AsyncSession, list_obj: List, payload: ListUpdate) -> List:
    fields = payload.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(list_obj, field, value)
    await db.commit()
    await db.refresh(list_obj)
    return list_obj


async def delete(db: AsyncSession, list_obj: List) -> None:
    await db.delete(list_obj)
    await db.commit()
