from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.services.auth import get_current_user
from app.services.billing_service import (
    DEFAULT_TIERS,
    TierDef,
    calculate_billing_breakdown,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_contracts(db: Session) -> list[Contract]:
    return db.query(Contract).join(Contract.bank).order_by(Contract.bank_id, Contract.effective_from.desc()).all()


@router.get("/billing-simulator", response_class=HTMLResponse)
def billing_simulator_get(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "billing_simulator.html",
        {
            "request": request,
            "user": current_user,
            "contracts": _get_contracts(db),
            "result": None,
            "total_txs": "",
            "selected_contract_id": "",
        },
    )


@router.post("/billing-simulator", response_class=HTMLResponse)
def billing_simulator_post(
    request: Request,
    total_txs: int = Form(...),
    contract_id: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contracts = _get_contracts(db)

    if contract_id:
        contract = db.query(Contract).filter(Contract.id == int(contract_id)).first()
        tiers = [TierDef(upper_bound=t.upper_bound, fee_per_tx=float(t.fee_per_tx)) for t in contract.pricing_tiers]
        min_fee = float(contract.min_monthly_fee)
        contract_label = f"{contract.bank.name} — {contract.version} (from {contract.effective_from})"
    else:
        tiers = DEFAULT_TIERS
        min_fee = 750.0
        contract_label = "Default tiers"

    result = calculate_billing_breakdown(total_txs, tiers, min_fee)
    result["contract_label"] = contract_label

    return templates.TemplateResponse(
        "billing_simulator.html",
        {
            "request": request,
            "user": current_user,
            "contracts": contracts,
            "result": result,
            "total_txs": total_txs,
            "selected_contract_id": contract_id,
        },
    )
