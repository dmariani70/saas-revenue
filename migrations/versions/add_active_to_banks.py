"""Add active field to banks."""
from alembic import op
import sqlalchemy as sa


revision = "add_active_banks"
down_revision = "f94f7f3d1303"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("banks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default="1"))


def downgrade():
    with op.batch_alter_table("banks", schema=None) as batch_op:
        batch_op.drop_column("active")
