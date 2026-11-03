"""Create user-owned tags and entry assignments.

Revision ID: f8a9b0c1d2e3
Revises: 3b7541e12ad5
Create Date: 2026-11-03

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f8a9b0c1d2e3"
down_revision = "3b7541e12ad5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_tags_user_name", "tags", ["user_id", sa.text("lower(name)")], unique=True)
    op.create_table(
        "entry_tags",
        sa.Column("entry_id", sa.BigInteger, sa.ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.BigInteger, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_entry_tags_tag_id", "entry_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_entry_tags_tag_id", table_name="entry_tags")
    op.drop_table("entry_tags")
    op.drop_table("tags")
