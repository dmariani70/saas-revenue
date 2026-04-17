import os
import sys

import fastapi
import sqlalchemy
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bank import Bank
from app.models.monthly_metric import MonthlyMetric
from app.services.auth import get_current_user
from app.models.user import User

APP_VERSION = "1.0.0"

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/about", response_class=HTMLResponse)
def about(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_banks = db.query(Bank).count()
    active_banks = db.query(Bank).filter_by(active=True).count()
    total_periods = db.query(MonthlyMetric).count()

    first = db.query(MonthlyMetric).order_by(MonthlyMetric.year, MonthlyMetric.month).first()
    last = db.query(MonthlyMetric).order_by(MonthlyMetric.year.desc(), MonthlyMetric.month.desc()).first()
    data_range = None
    if first and last:
        mn = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        data_range = f"{mn[first.month]} {first.year} – {mn[last.month]} {last.year}"

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite"):
        db_engine = "SQLite"
    elif db_url.startswith("postgresql"):
        db_engine = "PostgreSQL"
    else:
        db_engine = "Unknown"

    return templates.TemplateResponse("about.html", {
        "request": request,
        "user": current_user,
        "app_version": APP_VERSION,
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi.__version__,
        "sqlalchemy_version": sqlalchemy.__version__,
        "db_engine": db_engine,
        "total_banks": total_banks,
        "active_banks": active_banks,
        "total_periods": total_periods,
        "data_range": data_range,
    })
