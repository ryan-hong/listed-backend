"""rename_entry_visits_to_entry_logs

Renames entry_visits → entry_logs and aligns dependent identifiers:
- entry_media.visit_id  → entry_media.log_id
- list_entries.visit_count → list_entries.log_count
- entry_visits.visited_at → entry_logs.occurred_at
- index + FK constraint names follow the new noun.

Pure metadata rename — no data movement, no nullability changes.

Revision ID: d7e8f9a0b1c2
Revises: c5d6e7f8a9b0
Create Date: 2026-05-25

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. entry_media: drop FK + index that reference the old names, rename
    #    the column, then recreate the FK + index with the new names.
    op.drop_index("ix_entry_media_visit_id", table_name="entry_media")
    op.drop_constraint(
        "fk_entry_media_visit_id", "entry_media", type_="foreignkey"
    )
    op.alter_column("entry_media", "visit_id", new_column_name="log_id")

    # 2. Rename the table + its index + its per-visit timestamp column.
    op.drop_index("ix_entry_visits_entry_id", table_name="entry_visits")
    op.rename_table("entry_visits", "entry_logs")
    op.alter_column("entry_logs", "visited_at", new_column_name="occurred_at")
    op.create_index("ix_entry_logs_entry_id", "entry_logs", ["entry_id"])

    # 3. Recreate the FK + index on entry_media with new names, now pointing
    #    at entry_logs.
    op.create_foreign_key(
        "fk_entry_media_log_id",
        "entry_media",
        "entry_logs",
        ["log_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_entry_media_log_id", "entry_media", ["log_id"])

    # 4. Denormalized count column on list_entries.
    op.alter_column("list_entries", "visit_count", new_column_name="log_count")


def downgrade() -> None:
    op.alter_column("list_entries", "log_count", new_column_name="visit_count")

    op.drop_index("ix_entry_media_log_id", table_name="entry_media")
    op.drop_constraint(
        "fk_entry_media_log_id", "entry_media", type_="foreignkey"
    )
    op.alter_column("entry_media", "log_id", new_column_name="visit_id")

    op.drop_index("ix_entry_logs_entry_id", table_name="entry_logs")
    op.alter_column("entry_logs", "occurred_at", new_column_name="visited_at")
    op.rename_table("entry_logs", "entry_visits")
    op.create_index("ix_entry_visits_entry_id", "entry_visits", ["entry_id"])

    op.create_foreign_key(
        "fk_entry_media_visit_id",
        "entry_media",
        "entry_visits",
        ["visit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_entry_media_visit_id", "entry_media", ["visit_id"])
