"""rename_list_entries_to_entries

Rename the table and its indexes, constraints, and ID sequence in place.
Existing rows and foreign key relationships are preserved.

Revision ID: 3b7541e12ad5
Revises: d7e8f9a0b1c2
Create Date: 2026-10-10 16:11:28.438585

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3b7541e12ad5"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("list_entries", "entries")
    op.execute("ALTER INDEX ix_list_entries_list_id RENAME TO ix_entries_list_id")
    op.execute(
        "ALTER INDEX ix_list_entries_list_id_position RENAME TO ix_entries_list_id_position"
    )
    op.execute(
        "ALTER INDEX ux_list_entries_list_external RENAME TO ux_entries_list_external"
    )
    op.execute(
        "ALTER TABLE entries RENAME CONSTRAINT list_entries_pkey TO entries_pkey"
    )
    op.execute(
        "ALTER TABLE entries RENAME CONSTRAINT list_entries_list_id_fkey TO entries_list_id_fkey"
    )
    op.execute("ALTER SEQUENCE list_entries_id_seq RENAME TO entries_id_seq")


def downgrade() -> None:
    op.execute("ALTER SEQUENCE entries_id_seq RENAME TO list_entries_id_seq")
    op.execute(
        "ALTER TABLE entries RENAME CONSTRAINT entries_list_id_fkey TO list_entries_list_id_fkey"
    )
    op.execute(
        "ALTER TABLE entries RENAME CONSTRAINT entries_pkey TO list_entries_pkey"
    )
    op.execute(
        "ALTER INDEX ux_entries_list_external RENAME TO ux_list_entries_list_external"
    )
    op.execute(
        "ALTER INDEX ix_entries_list_id_position RENAME TO ix_list_entries_list_id_position"
    )
    op.execute("ALTER INDEX ix_entries_list_id RENAME TO ix_list_entries_list_id")
    op.rename_table("entries", "list_entries")
