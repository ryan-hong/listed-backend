import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from listed_backend.database import Base


class EntryType(str, enum.Enum):
    restaurant = "restaurant"
    movie = "movie"
    travel = "travel"
    custom = "custom"


class ListEntry(Base):
    __tablename__ = "list_entries"
    __table_args__ = (
        Index("ix_list_entries_list_id_position", "list_id", "position"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_favourited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    media: Mapped[list["EntryMedia"]] = relationship(
        cascade="all, delete-orphan",
        order_by="EntryMedia.position",
    )


class EntryMedia(Base):
    __tablename__ = "entry_media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("list_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

