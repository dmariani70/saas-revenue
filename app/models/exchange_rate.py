from datetime import datetime
from sqlalchemy import String, Numeric, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("currency", "year", "month", "strategy", name="uq_fx_currency_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_usd: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    strategy: Mapped[str] = mapped_column(String(16), nullable=False, default="first_day")
    source: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
