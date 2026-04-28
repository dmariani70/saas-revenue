import csv
import io
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.bank import Bank
from app.models.contract import Contract
from app.models.import_record import Import, ImportRow
from app.models.monthly_metric import MonthlyMetric
from app.models.audit_log import AuditLog
from app.services import billing_service, fx_service
from app.services.billing_service import TierDef


@dataclass
class ImportResult:
    success: bool
    row_count: int = 0
    errors: list[str] = field(default_factory=list)
    import_id: Optional[int] = None


def _parse_date(value: str) -> date:
    from datetime import datetime, timedelta
    stripped = value.strip()
    # Excel serial date (e.g. 46055 → 2026-01-30)
    if stripped.isdigit():
        return (date(1899, 12, 30) + timedelta(days=int(stripped)))
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {value!r}")


def _get_active_contract(db: Session, bank_id: int, ref_date: date) -> Optional[Contract]:
    return (
        db.query(Contract)
        .filter(Contract.bank_id == bank_id, Contract.effective_from <= ref_date)
        .order_by(Contract.effective_from.desc())
        .first()
    )


def import_file(
    db: Session,
    bank: Bank,
    filename: str,
    content: bytes,
    user_id: Optional[int],
    fx_strategy: str = "first_day",
    file_hash: Optional[str] = None,
) -> ImportResult:
    """
    Parse a CSV/TXT file for a bank, persist rows, compute monthly metrics.
    A reimport for the same (bank, year, month) replaces previous data.
    """
    text = content.decode("utf-8-sig", errors="replace")
    first_line = text.split("\n")[0]
    delimiter = "\t" if "\t" in first_line else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    # Normalise column names (lowercase, strip)
    raw_rows = []
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):  # row 1 is header
        norm = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        raw_rows.append((i, norm))

    if not raw_rows:
        return ImportResult(success=False, errors=["File is empty or has no data rows"])

    # Detect period from the data (all rows should belong to 1 month)
    # Group rows by (year, month)
    from collections import defaultdict
    groups: dict[tuple[int, int], list] = defaultdict(list)

    for line_no, norm in raw_rows:
        try:
            tx_date = _parse_date(norm.get("date", norm.get("fecha", "")))
        except ValueError as e:
            errors.append(f"Line {line_no}: {e}")
            continue
        try:
            amount = float(norm.get("amount", norm.get("monto", 0)) or 0)
            count = int(float(norm.get("count", norm.get("count", 1)) or 1))
            file_id = str(norm.get("file_id", norm.get("file_id", "")))
            scheme = norm.get("scheme", norm.get("scheme", "")).upper() or None
        except (ValueError, KeyError) as e:
            errors.append(f"Line {line_no}: {e}")
            continue

        groups[(tx_date.year, tx_date.month)].append(
            {"tx_date": tx_date, "file_id": file_id, "scheme": scheme,
             "amount_orig": amount, "tx_count": count}
        )

    if not groups:
        return ImportResult(success=False, errors=errors or ["No valid rows parsed"])

    import_records = []
    for (year, month), rows in groups.items():
        import_records.append(
            _process_period(db, bank, filename, year, month, rows, user_id, fx_strategy, errors, file_hash)
        )

    db.commit()

    # Audit
    db.add(AuditLog(
        user_id=user_id,
        action="import_file",
        entity="import",
        detail={"bank": bank.code, "filename": filename,
                "periods": [f"{r.year}/{r.month}" for r in import_records]},
    ))
    db.commit()

    total_rows = sum(len(groups[k]) for k in groups)
    return ImportResult(
        success=True,
        row_count=total_rows,
        errors=errors,
        import_id=import_records[0].id if import_records else None,
    )


def _process_period(
    db: Session,
    bank: Bank,
    filename: str,
    year: int,
    month: int,
    rows: list[dict],
    user_id: Optional[int],
    fx_strategy: str,
    errors: list[str],
    file_hash: Optional[str] = None,
) -> Import:
    # Delete previous import for this period
    prev = db.query(Import).filter_by(bank_id=bank.id, year=year, month=month).first()
    if prev:
        db.delete(prev)
        db.flush()

    imp = Import(
        bank_id=bank.id, year=year, month=month,
        filename=filename, file_hash=file_hash, status="ok",
        imported_by=user_id, row_count=len(rows),
    )
    db.add(imp)
    db.flush()

    for r in rows:
        db.add(ImportRow(import_id=imp.id, **r))

    # Aggregate
    total_txs = sum(r["tx_count"] for r in rows)
    total_amount_orig = sum(r["amount_orig"] for r in rows)

    # FX
    fx_rec = fx_service.get_or_fetch_rate(db, bank.currency, year, month, fx_strategy)
    rate = float(fx_rec.rate_usd) if fx_rec else None
    amount_usd = total_amount_orig / rate if rate else 0.0
    avg_per_tx_usd = (amount_usd / total_txs) if total_txs else 0.0

    # Billing
    ref_date = date(year, month, 1)
    contract = _get_active_contract(db, bank.id, ref_date)
    contract_amount = None
    total_bill = None
    if contract and contract.pricing_tiers:
        tiers = [TierDef(t.upper_bound, float(t.fee_per_tx)) for t in contract.pricing_tiers]
        contract_amount = billing_service.calculate_billing(total_txs, tiers)
        total_bill = billing_service.total_to_bill(total_txs, tiers, float(contract.min_monthly_fee))

    # Upsert monthly_metric
    metric = db.query(MonthlyMetric).filter_by(bank_id=bank.id, year=year, month=month).first()
    if metric:
        metric.total_txs = total_txs
        metric.amount_orig = total_amount_orig
        metric.currency = bank.currency
        metric.amount_usd = amount_usd
        metric.fx_rate_id = fx_rec.id if fx_rec else None
        metric.avg_per_tx_usd = avg_per_tx_usd
        metric.contract_amount = contract_amount
        metric.total_to_bill = total_bill
    else:
        db.add(MonthlyMetric(
            bank_id=bank.id, year=year, month=month,
            total_txs=total_txs, amount_orig=total_amount_orig,
            currency=bank.currency, amount_usd=amount_usd,
            fx_rate_id=fx_rec.id if fx_rec else None,
            avg_per_tx_usd=avg_per_tx_usd,
            contract_amount=contract_amount,
            total_to_bill=total_bill,
        ))

    db.flush()
    return imp


def recalculate_billing_for_bank(db: Session, bank_id: int) -> int:
    """Recalculate contract_amount and total_to_bill for all monthly_metrics of a bank.
    Called after a contract is created or edited. Returns number of periods updated."""
    metrics = db.query(MonthlyMetric).filter_by(bank_id=bank_id).all()
    for metric in metrics:
        ref_date = date(metric.year, metric.month, 1)
        contract = _get_active_contract(db, bank_id, ref_date)
        if contract and contract.pricing_tiers:
            tiers = [TierDef(t.upper_bound, float(t.fee_per_tx)) for t in contract.pricing_tiers]
            metric.contract_amount = billing_service.calculate_billing(metric.total_txs, tiers)
            metric.total_to_bill = billing_service.total_to_bill(
                metric.total_txs, tiers, float(contract.min_monthly_fee)
            )
        else:
            metric.contract_amount = None
            metric.total_to_bill = None
    db.commit()
    return len(metrics)
