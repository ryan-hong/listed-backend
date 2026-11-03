from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from listed_backend.database import get_db
from listed_backend.dependencies.auth import get_current_user
from listed_backend.models.user import User
from listed_backend.schemas.tag import TagResponse, TagWrite
from listed_backend.services import tags as tags_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def get_tags(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await tags_service.list_for_user(db, user)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    body: TagWrite,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await tags_service.create(db, user, body)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int, body: TagWrite,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    tag = await tags_service.get_owned(db, user, tag_id)
    return await tags_service.update(db, tag, body)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    tag = await tags_service.get_owned(db, user, tag_id)
    await tags_service.delete(db, tag)
