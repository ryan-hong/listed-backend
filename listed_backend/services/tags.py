from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from listed_backend.models.tag import Tag
from listed_backend.models.user import User
from listed_backend.schemas.tag import TagWrite


async def list_for_user(db: AsyncSession, user: User) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user.id).order_by(func.lower(Tag.name), Tag.id)
    )
    return list(result.scalars().all())


async def get_owned(db: AsyncSession, user: User, tag_id: int) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


async def resolve_owned(db: AsyncSession, user: User, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(
        select(Tag)
        .where(Tag.user_id == user.id, Tag.id.in_(tag_ids))
        .order_by(Tag.id)
        # Keep tags alive until entry assignment commits.
        .with_for_update(read=True)
    )
    tags = list(result.scalars().all())
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=404, detail="Tag not found")
    return tags


async def _save(db: AsyncSession, tag: Tag) -> Tag:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # Only translate this constraint; unrelated integrity failures must surface.
        error = exc.orig
        while error is not None:
            name = getattr(error, "constraint_name", None)
            if name is None:
                name = getattr(getattr(error, "diag", None), "constraint_name", None)
            if name == "uq_tags_user_name" or "UNIQUE constraint failed: index 'uq_tags_user_name'" in str(error):
                raise HTTPException(status_code=409, detail="A tag with this name already exists") from None
            error = error.__cause__
        raise
    await db.refresh(tag)
    return tag


async def create(db: AsyncSession, user: User, payload: TagWrite) -> Tag:
    tag = Tag(user_id=user.id, name=payload.name)
    db.add(tag)
    return await _save(db, tag)


async def update(db: AsyncSession, tag: Tag, payload: TagWrite) -> Tag:
    tag.name = payload.name
    return await _save(db, tag)


async def delete(db: AsyncSession, tag: Tag) -> None:
    await db.delete(tag)
    await db.commit()
