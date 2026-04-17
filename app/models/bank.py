from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    # JSON: {"date_col": "date", "file_id_col": "file_id", ...}
    import_format: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    contracts: Mapped[list["Contract"]] = relationship(back_populates="bank", order_by="Contract.effective_from")
    imports: Mapped[list["Import"]] = relationship(back_populates="bank")
    metrics: Mapped[list["MonthlyMetric"]] = relationship(back_populates="bank")
