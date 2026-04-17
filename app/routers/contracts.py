from datetime import date
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bank import Bank
from app.models.contract import Contract, PricingTier
from app.models.user import User
from app.services.auth import require_admin
from app.services.importer import recalculate_billing_for_bank

router = APIRouter(prefix="/contracts")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_contracts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    contracts = db.query(Contract).join(Bank).order_by(Bank.name, Contract.effective_from.desc()).all()
    banks = db.query(Bank).filter_by(active=True).order_by(Bank.name).all()
    return templates.TemplateResponse(
        "contracts.html",
        {"request": request, "user": current_user, "contracts": contracts, "banks": banks},
    )


@router.post("/new")
def create_contract(
    bank_id: int = Form(...),
    version: str = Form("v1"),
    effective_from: str = Form(...),
    min_monthly_fee: float = Form(750.0),
    # tiers as parallel arrays
    tier_upper: list[int] = Form(...),
    tier_fee: list[float] = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    contract = Contract(
        bank_id=bank_id,
        version=version,
        effective_from=date.fromisoformat(effective_from),
        min_monthly_fee=min_monthly_fee,
    )
    db.add(contract)
    db.flush()
    for ub, fee in zip(tier_upper, tier_fee):
        db.add(PricingTier(contract_id=contract.id, upper_bound=ub, fee_per_tx=fee))
    db.commit()
    recalculate_billing_for_bank(db, bank_id)
    return RedirectResponse("/contracts", status_code=302)


@router.get("/{contract_id}/edit", response_class=HTMLResponse)
def edit_contract_form(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    c = db.get(Contract, contract_id)
    if not c:
        return RedirectResponse("/contracts", status_code=302)
    banks = db.query(Bank).filter_by(active=True).order_by(Bank.name).all()
    return templates.TemplateResponse(
        "contract_edit.html",
        {"request": request, "user": current_user, "contract": c, "banks": banks},
    )


@router.post("/{contract_id}/edit")
def edit_contract(
    contract_id: int,
    bank_id: int = Form(...),
    version: str = Form("v1"),
    effective_from: str = Form(...),
    min_monthly_fee: float = Form(750.0),
    tier_upper: list[int] = Form(...),
    tier_fee: list[float] = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    c = db.get(Contract, contract_id)
    if not c:
        return RedirectResponse("/contracts", status_code=302)
    c.bank_id = bank_id
    c.version = version
    c.effective_from = date.fromisoformat(effective_from)
    c.min_monthly_fee = min_monthly_fee
    for tier in list(c.pricing_tiers):
        db.delete(tier)
    db.flush()
    for ub, fee in zip(tier_upper, tier_fee):
        db.add(PricingTier(contract_id=c.id, upper_bound=ub, fee_per_tx=fee))
    db.commit()
    recalculate_billing_for_bank(db, bank_id)
    return RedirectResponse("/contracts", status_code=302)


@router.post("/{contract_id}/delete")
@router.delete("/{contract_id}/delete")
def delete_contract(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    c = db.get(Contract, contract_id)
    if c:
        db.delete(c)
        db.commit()

    # HTMX request: reload page
    if request.headers.get("HX-Request"):
        return HTMLResponse('<script>window.location.reload()</script>')

    return RedirectResponse("/contracts", status_code=302)
