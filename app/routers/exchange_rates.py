import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.exchange_rate import ExchangeRate
from app.models.user import User
from app.services.auth import require_admin, get_current_user
from app.services import fx_service

router = APIRouter(prefix="/exchange-rates")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_rates(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rates = db.query(ExchangeRate).order_by(
        ExchangeRate.currency, ExchangeRate.year.asc(), ExchangeRate.month.asc()
    ).all()

    loaded_currencies = sorted({r.currency for r in rates})

    rates_json = json.dumps([
        {"currency": r.currency, "year": r.year, "month": r.month,
         "rate_usd": float(r.rate_usd), "strategy": r.strategy, "source": r.source or ""}
        for r in rates
    ])

    # For table display keep reverse-chrono order
    rates_display = sorted(rates, key=lambda r: (r.currency, -r.year, -r.month))

    return templates.TemplateResponse(
        "exchange_rates.html",
        {
            "request": request,
            "user": current_user,
            "rates": rates_display,
            "loaded_currencies": loaded_currencies,
            "rates_json": rates_json,
        },
    )



@router.post("/sync")
def sync_rates(
    overwrite: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Fetch rates from API for every currency in DB.
    overwrite=False → only fill missing months.
    overwrite=True  → replace all existing records with fresh API data.
    """
    from collections import defaultdict

    rows = db.query(ExchangeRate).all()

    currency_range: dict = defaultdict(lambda: {"min": None, "max": None})
    records_by_key: dict = {}
    strategy = "first_day"

    for r in rows:
        period = (r.year, r.month)
        cr = currency_range[r.currency]
        if cr["min"] is None or period < cr["min"]:
            cr["min"] = period
        if cr["max"] is None or period > cr["max"]:
            cr["max"] = period
        records_by_key[(r.currency, r.year, r.month, r.strategy)] = r

    from datetime import date
    today = date.today()
    current_period = (today.year, today.month)

    updated = created = skipped = failed = 0

    for currency, cr in currency_range.items():
        if currency == "USD":
            continue
        y, m = cr["min"]
        max_y, max_m = max(cr["max"], current_period)
        while (y, m) <= (max_y, max_m):
            key = (currency, y, m, strategy)
            existing = records_by_key.get(key)
            if existing and not overwrite:
                skipped += 1
            else:
                rate = fx_service._provider.get_rate(currency, y, m)
                if rate is not None:
                    if existing:
                        existing.rate_usd = rate
                        existing.source = "openexchangerates.org"
                        updated += 1
                    else:
                        db.add(ExchangeRate(
                            currency=currency, year=y, month=m,
                            rate_usd=rate, strategy=strategy,
                            source="openexchangerates.org",
                        ))
                        created += 1
                else:
                    failed += 1
            m += 1
            if m > 12:
                y, m = y + 1, 1

    db.commit()
    return JSONResponse({"updated": updated, "created": created, "skipped": skipped, "failed": failed})


@router.post("/{rate_id}/delete")
@router.delete("/{rate_id}/delete")
def delete_rate(
    rate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    r = db.get(ExchangeRate, rate_id)
    if r:
        db.delete(r)
        db.commit()

    # HTMX request: reload page
    if request.headers.get("HX-Request"):
        return HTMLResponse('<script>window.location.reload()</script>')

    return RedirectResponse("/exchange-rates", status_code=302)
