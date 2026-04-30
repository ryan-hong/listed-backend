"""add first, last, display name to users table

Revision ID: 887c171928c3
Revises: e418ebcb9ae5
Create Date: 2026-03-22 00:45:28.448560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '887c171928c3'
down_revision: Union[str, Sequence[str], None] = 'e418ebcb9ae5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "display_name")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
