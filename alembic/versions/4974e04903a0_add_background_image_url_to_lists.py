"""add_background_image_url_to_lists

Revision ID: 4974e04903a0
Revises: b2c3d4e5f6a7
Create Date: 2026-04-18 14:55:43.047939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4974e04903a0'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lists",
        sa.Column("background_image_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lists", "background_image_url")
