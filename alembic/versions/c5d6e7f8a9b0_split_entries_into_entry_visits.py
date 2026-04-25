"""split_entries_into_entry_visits

Splits list_entries into the canonical "thing" (list_entries) and per-occurrence
visits (entry_visits). Per-visit fields (note, rating, media) move to
entry_visits; list_entries gains visit_count + external_source/external_id for
user-driven dedup at add time.

Revision ID: c5d6e7f8a9b0
Revises: 4974e04903a0
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "4974e04903a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. entry_visits table
    op.create_table(
        "entry_visits",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "entry_id",
            sa.BigInteger(),
            sa.ForeignKey("list_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_entry_visits_entry_id", "entry_visits", ["entry_id"])

    # 2. New columns on list_entries
    op.add_column(
        "list_entries",
        sa.Column(
            "visit_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.add_column(
        "list_entries",
        sa.Column("external_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "list_entries",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "ux_list_entries_list_external",
        "list_entries",
        ["list_id", "external_source", "external_id"],
        unique=True,
        postgresql_where=sa.text(
            "external_source IS NOT NULL AND external_id IS NOT NULL"
        ),
    )

    # 3. Backfill: one synthetic visit per existing entry, preserving
    #    note/rating and timestamps.
    op.execute(
        """
        INSERT INTO entry_visits (
            entry_id, note, rating, visited_at, created_at, updated_at
        )
        SELECT id, note, rating, created_at, created_at, updated_at
        FROM list_entries
        """
    )

    # 4. Repoint entry_media: entry_id -> visit_id
    op.add_column(
        "entry_media",
        sa.Column("visit_id", sa.BigInteger(), nullable=True),
    )
    op.execute(
        """
        UPDATE entry_media em
        SET visit_id = ev.id
        FROM entry_visits ev
        WHERE ev.entry_id = em.entry_id
        """
    )
    op.alter_column("entry_media", "visit_id", nullable=False)
    op.create_foreign_key(
        "fk_entry_media_visit_id",
        "entry_media",
        "entry_visits",
        ["visit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_entry_media_visit_id", "entry_media", ["visit_id"])
    op.drop_index("ix_entry_media_entry_id", table_name="entry_media")
    op.drop_constraint(
        "entry_media_entry_id_fkey", "entry_media", type_="foreignkey"
    )
    op.drop_column("entry_media", "entry_id")

    # 5. Drop migrated columns from list_entries
    op.drop_column("list_entries", "rating")
    op.drop_column("list_entries", "note")


def downgrade() -> None:
    # Restore note/rating on list_entries from the earliest visit per entry.
    # Note: data from additional visits beyond the first is lost on downgrade.
    op.add_column("list_entries", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("list_entries", sa.Column("rating", sa.Float(), nullable=True))
    op.execute(
        """
        UPDATE list_entries le
        SET note = ev.note, rating = ev.rating
        FROM (
            SELECT DISTINCT ON (entry_id) entry_id, note, rating
            FROM entry_visits
            ORDER BY entry_id, created_at ASC, id ASC
        ) ev
        WHERE le.id = ev.entry_id
        """
    )

    # Restore entry_media.entry_id from visit_id.
    op.add_column(
        "entry_media", sa.Column("entry_id", sa.BigInteger(), nullable=True)
    )
    op.execute(
        """
        UPDATE entry_media em
        SET entry_id = ev.entry_id
        FROM entry_visits ev
        WHERE ev.id = em.visit_id
        """
    )
    op.alter_column("entry_media", "entry_id", nullable=False)
    op.create_foreign_key(
        "entry_media_entry_id_fkey",
        "entry_media",
        "list_entries",
        ["entry_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_entry_media_entry_id", "entry_media", ["entry_id"])
    op.drop_index("ix_entry_media_visit_id", table_name="entry_media")
    op.drop_constraint(
        "fk_entry_media_visit_id", "entry_media", type_="foreignkey"
    )
    op.drop_column("entry_media", "visit_id")

    op.drop_index("ux_list_entries_list_external", table_name="list_entries")
    op.drop_column("list_entries", "external_id")
    op.drop_column("list_entries", "external_source")
    op.drop_column("list_entries", "visit_count")

    op.drop_index("ix_entry_visits_entry_id", table_name="entry_visits")
    op.drop_table("entry_visits")
