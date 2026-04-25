import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from listed_backend.database import Base


class List(Base):
    __tablename__ = "lists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    emoji: Mapped[str | None] = mapped_column(String(20), nullable=True)
    background_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
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

    # Relationships
    entries: Mapped[list["ListEntry"]] = relationship(
        cascade="all, delete-orphan",
        order_by="ListEntry.position",
    )
