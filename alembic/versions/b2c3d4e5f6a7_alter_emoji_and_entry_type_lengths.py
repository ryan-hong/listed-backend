"""alter_emoji_and_entry_type_lengths

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "lists",
        "emoji",
        type_=sa.String(20),
        existing_type=sa.String(10),
        existing_nullable=True,
    )
    op.alter_column(
        "list_entries",
        "entry_type",
        type_=sa.String(50),
        existing_type=sa.String(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "list_entries",
        "entry_type",
        type_=sa.String(),
        existing_type=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        "lists",
        "emoji",
        type_=sa.String(10),
        existing_type=sa.String(20),
        existing_nullable=True,
    )
