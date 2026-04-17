from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MonthlyMetric(Base):
    __tablename__ = "monthly_metrics"
    __table_args__ = (
        UniqueConstraint("bank_id", "year", "month", name="uq_metric_bank_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    total_txs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount_orig: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount_usd: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    fx_rate_id: Mapped[int] = mapped_column(ForeignKey("exchange_rates.id"), nullable=True)
    avg_per_tx_usd: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    contract_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)
    total_to_bill: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)

    bank: Mapped["Bank"] = relationship(back_populates="metrics")
    fx_rate: Mapped["ExchangeRate"] = relationship()
