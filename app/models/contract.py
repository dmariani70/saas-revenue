from datetime import date
from sqlalchemy import ForeignKey, String, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    min_monthly_fee: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=750.0)

    bank: Mapped["Bank"] = relationship(back_populates="contracts")
    pricing_tiers: Mapped[list["PricingTier"]] = relationship(
        back_populates="contract",
        order_by="PricingTier.upper_bound",
        cascade="all, delete-orphan",
    )


class PricingTier(Base):
    __tablename__ = "pricing_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    upper_bound: Mapped[int] = mapped_column(nullable=False)
    fee_per_tx: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)

    contract: Mapped["Contract"] = relationship(back_populates="pricing_tiers")
