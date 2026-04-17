from datetime import datetime, date
from sqlalchemy import ForeignKey, String, Integer, Numeric, DateTime, Date, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|ok|error
    imported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, nullable=True)

    bank: Mapped["Bank"] = relationship(back_populates="imports")
    rows: Mapped[list["ImportRow"]] = relationship(back_populates="import_record", cascade="all, delete-orphan")


class ImportRow(Base):
    __tablename__ = "import_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id"), nullable=False)
    tx_date: Mapped[date] = mapped_column(Date, nullable=False)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scheme: Mapped[str] = mapped_column(String(32), nullable=True)
    amount_orig: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)

    import_record: Mapped["Import"] = relationship(back_populates="rows")
