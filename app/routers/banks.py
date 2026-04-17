import json
import os
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bank import Bank
from app.models.user import User
from app.services.auth import get_current_user, require_admin
from app.services.currencies import get_iso_currencies
from app.services.reporting import get_bank_metrics, MONTH_NAMES

router = APIRouter(prefix="/banks")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_banks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    banks = db.query(Bank).order_by(Bank.name).all()
    return templates.TemplateResponse(
        "banks.html", {"request": request, "user": current_user, "banks": banks}
    )


# /new MUST come before /{bank_id} to avoid "new" being parsed as int
@router.get("/new", response_class=HTMLResponse)
def new_bank_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        "bank_form.html",
        {"request": request, "user": current_user, "bank": None,
         "currencies": get_iso_currencies()},
    )


_LOGO_DIR = "app/static/logos"
_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


async def _save_logo(file: UploadFile, code: str) -> None:
    if not file or not file.filename:
        return
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _ALLOWED_EXTS:
        return
    data = await file.read()
    if not data:
        return
    os.makedirs(_LOGO_DIR, exist_ok=True)
    dest = os.path.join(_LOGO_DIR, f"{code.lower()}.png")
    with open(dest, "wb") as f:
        f.write(data)


@router.post("/new")
async def create_bank(
    name: str = Form(...),
    code: str = Form(...),
    currency: str = Form(...),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    bank_code = code.upper()
    db.add(Bank(name=name, code=bank_code, currency=currency.upper(), import_format={}))
    db.commit()
    await _save_logo(logo, bank_code)
    return RedirectResponse("/banks", status_code=302)


@router.get("/{bank_id}", response_class=HTMLResponse)
def bank_detail(
    bank_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bank = db.get(Bank, bank_id)
    if not bank:
        return RedirectResponse("/banks", status_code=302)
    metrics = get_bank_metrics(db, bank_id)
    labels = [f"{MONTH_NAMES[m.month]} {m.year}" for m in metrics]
    usd_data = [float(m.amount_usd or 0) for m in metrics]
    tx_data = [int(m.total_txs or 0) for m in metrics]
    metrics_json = json.dumps([
        {
            "year": m.year, "month": m.month,
            "total_txs": int(m.total_txs or 0),
            "amount_orig": float(m.amount_orig or 0),
            "amount_usd": float(m.amount_usd or 0),
            "avg_per_tx_usd": float(m.avg_per_tx_usd or 0),
            "contract_amount": float(m.contract_amount) if m.contract_amount is not None else None,
            "total_to_bill": float(m.total_to_bill) if m.total_to_bill is not None else None,
        }
        for m in metrics
    ])
    return templates.TemplateResponse(
        "bank_detail.html",
        {
            "request": request, "user": current_user,
            "bank": bank, "metrics": metrics,
            "month_names": MONTH_NAMES,
            "chart_labels": json.dumps(labels),
            "chart_usd": json.dumps(usd_data),
            "chart_txs": json.dumps(tx_data),
            "metrics_json": metrics_json,
        },
    )


@router.post("/{bank_id}/toggle-active", response_class=HTMLResponse)
def toggle_bank_active(
    bank_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    bank = db.get(Bank, bank_id)
    if bank:
        bank.active = not bank.active
        db.commit()

    # HTMX request: reload page to show bank in correct section
    if request.headers.get("HX-Request"):
        return HTMLResponse('<script>window.location.reload()</script>')

    return RedirectResponse("/", status_code=302)


@router.get("/{bank_id}/edit", response_class=HTMLResponse)
def edit_bank_form(
    bank_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    bank = db.get(Bank, bank_id)
    return templates.TemplateResponse(
        "bank_form.html",
        {"request": request, "user": current_user, "bank": bank,
         "currencies": get_iso_currencies()},
    )


@router.post("/{bank_id}/edit")
async def edit_bank(
    bank_id: int,
    name: str = Form(...),
    currency: str = Form(...),
    active: bool = Form(False),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    bank = db.get(Bank, bank_id)
    if bank:
        bank.name = name
        bank.currency = currency.upper()
        bank.active = active
        db.commit()
        await _save_logo(logo, bank.code)
    return RedirectResponse(f"/banks/{bank_id}", status_code=302)
