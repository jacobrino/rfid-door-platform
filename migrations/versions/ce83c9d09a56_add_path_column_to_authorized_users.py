"""add path column to authorized_users

Revision ID: ce83c9d09a56
Revises: 92db774ea127
Create Date: 2026-04-16 16:53:39.058663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce83c9d09a56'
down_revision: Union[str, Sequence[str], None] = '92db774ea127'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("authorized_users", sa.Column("path", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("authorized_users", "path")
