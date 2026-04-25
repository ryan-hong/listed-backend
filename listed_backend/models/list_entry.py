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
        Index(
            "ux_list_entries_list_external",
            "list_id",
            "external_source",
            "external_id",
            unique=True,
            postgresql_where=text(
                "external_source IS NOT NULL AND external_id IS NOT NULL"
            ),
        ),
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
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_favourited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Denormalized count of entry_visits rows. Maintained by app code on
    # visit insert/delete so list views can render without a join+aggregate.
    visit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    # Optional dedup key (e.g. ("google_places", "ChIJ...") or ("tmdb", "603")).
    # Unique per list when both are non-null — drives the "you've logged this
    # before" prompt at add time.
    external_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'{}'::jsonb")
    )
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

    visits: Mapped[list["EntryVisit"]] = relationship(
        cascade="all, delete-orphan",
        order_by="EntryVisit.visited_at.desc().nullslast(), EntryVisit.created_at.desc()",
    )


class EntryVisit(Base):
    __tablename__ = "entry_visits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("list_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    visited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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

    media: Mapped[list["EntryMedia"]] = relationship(
        cascade="all, delete-orphan",
        order_by="EntryMedia.position",
    )


class EntryMedia(Base):
    __tablename__ = "entry_media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entry_visits.id", ondelete="CASCADE"),
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
