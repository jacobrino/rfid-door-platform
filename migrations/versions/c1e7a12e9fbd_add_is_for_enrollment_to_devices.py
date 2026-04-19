"""add is_for_enrollment to devices

Revision ID: c1e7a12e9fbd
Revises: ce83c9d09a56
Create Date: 2026-04-18 20:17:55.497345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1e7a12e9fbd'
down_revision: Union[str, Sequence[str], None] = 'ce83c9d09a56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("is_for_enrollment", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("devices", "is_for_enrollment")