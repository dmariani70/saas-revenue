"""add file_hash to imports

Revision ID: f94f7f3d1303
Revises: 0001
Create Date: 2026-04-17 10:34:40.576677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f94f7f3d1303'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('imports', sa.Column('file_hash', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('imports', 'file_hash')
