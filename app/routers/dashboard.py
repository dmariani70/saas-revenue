from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.reporting import get_all_banks_latest, get_inactive_banks_latest, MONTH_NAMES

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = get_all_banks_latest(db)
    inactive_rows = get_inactive_banks_latest(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request, "user": current_user,
            "rows": rows, "inactive_rows": inactive_rows,
            "month_names": MONTH_NAMES,
        },
    )
