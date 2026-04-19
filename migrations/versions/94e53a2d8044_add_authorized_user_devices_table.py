"""add authorized_user_devices table

Revision ID: 94e53a2d8044
Revises: c1e7a12e9fbd
Create Date: 2026-04-19 14:15:29.305475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94e53a2d8044'
down_revision: Union[str, Sequence[str], None] = 'c1e7a12e9fbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "authorized_user_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("authorized_user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["authorized_user_id"], ["authorized_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("authorized_user_id", "device_id", name="uq_authorized_user_device"),
    )
    op.create_index(op.f("ix_authorized_user_devices_id"), "authorized_user_devices", ["id"], unique=False)
    op.create_index(op.f("ix_authorized_user_devices_authorized_user_id"), "authorized_user_devices", ["authorized_user_id"], unique=False)
    op.create_index(op.f("ix_authorized_user_devices_device_id"), "authorized_user_devices", ["device_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_authorized_user_devices_device_id"), table_name="authorized_user_devices")
    op.drop_index(op.f("ix_authorized_user_devices_authorized_user_id"), table_name="authorized_user_devices")
    op.drop_index(op.f("ix_authorized_user_devices_id"), table_name="authorized_user_devices")
    op.drop_table("authorized_user_devices")