"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-16
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="viewer"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "banks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("code", sa.String(16), unique=True, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("import_format", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bank_id", sa.Integer, sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("min_monthly_fee", sa.Numeric(12, 4), nullable=False, server_default="750"),
    )

    op.create_table(
        "pricing_tiers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("contract_id", sa.Integer, sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("upper_bound", sa.Integer, nullable=False),
        sa.Column("fee_per_tx", sa.Numeric(10, 6), nullable=False),
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("rate_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("strategy", sa.String(16), nullable=False, server_default="first_day"),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("currency", "year", "month", "strategy", name="uq_fx_currency_period"),
    )

    op.create_table(
        "imports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bank_id", sa.Integer, sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("imported_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("imported_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("row_count", sa.Integer, server_default="0"),
        sa.Column("errors", sa.JSON, nullable=True),
    )

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("import_id", sa.Integer, sa.ForeignKey("imports.id"), nullable=False),
        sa.Column("tx_date", sa.Date, nullable=False),
        sa.Column("file_id", sa.String(64), nullable=False),
        sa.Column("scheme", sa.String(32), nullable=True),
        sa.Column("amount_orig", sa.Numeric(18, 4), nullable=False),
        sa.Column("tx_count", sa.Integer, nullable=False),
    )

    op.create_table(
        "monthly_metrics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bank_id", sa.Integer, sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("total_txs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("amount_orig", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("amount_usd", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("fx_rate_id", sa.Integer, sa.ForeignKey("exchange_rates.id"), nullable=True),
        sa.Column("avg_per_tx_usd", sa.Numeric(18, 6), nullable=True),
        sa.Column("contract_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_to_bill", sa.Numeric(18, 4), nullable=True),
        sa.UniqueConstraint("bank_id", "year", "month", name="uq_metric_bank_period"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("monthly_metrics")
    op.drop_table("import_rows")
    op.drop_table("imports")
    op.drop_table("exchange_rates")
    op.drop_table("pricing_tiers")
    op.drop_table("contracts")
    op.drop_table("banks")
    op.drop_table("users")
