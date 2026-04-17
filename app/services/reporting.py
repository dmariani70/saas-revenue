from datetime import date

from sqlalchemy.orm import Session

from app.models.monthly_metric import MonthlyMetric
from app.models.bank import Bank


def _exclude_current_month(query, today: date | None = None):
    """Filter out the in-progress current month from any MonthlyMetric query."""
    t = today or date.today()
    return query.filter(
        ~((MonthlyMetric.year == t.year) & (MonthlyMetric.month == t.month))
    )


def get_bank_metrics(db: Session, bank_id: int) -> list[MonthlyMetric]:
    return (
        _exclude_current_month(
            db.query(MonthlyMetric).filter_by(bank_id=bank_id)
        )
        .order_by(MonthlyMetric.year, MonthlyMetric.month)
        .all()
    )


def get_all_banks_latest(db: Session) -> list[dict]:
    """Returns the latest complete monthly metric per active bank for the dashboard."""
    banks = db.query(Bank).filter_by(active=True).order_by(Bank.name).all()
    result = []
    for bank in banks:
        latest = (
            _exclude_current_month(
                db.query(MonthlyMetric).filter_by(bank_id=bank.id)
            )
            .order_by(MonthlyMetric.year.desc(), MonthlyMetric.month.desc())
            .first()
        )
        result.append({"bank": bank, "latest": latest})
    return result


def get_inactive_banks_latest(db: Session) -> list[dict]:
    """Returns the latest complete monthly metric per inactive bank for the dashboard."""
    banks = db.query(Bank).filter_by(active=False).order_by(Bank.name).all()
    result = []
    for bank in banks:
        latest = (
            _exclude_current_month(
                db.query(MonthlyMetric).filter_by(bank_id=bank.id)
            )
            .order_by(MonthlyMetric.year.desc(), MonthlyMetric.month.desc())
            .first()
        )
        result.append({"bank": bank, "latest": latest})
    return result


MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
