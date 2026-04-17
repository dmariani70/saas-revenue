import hashlib

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.bank import Bank
from app.models.import_record import Import
from app.models.user import User
from app.services.auth import require_admin
from app.services.importer import import_file

router = APIRouter(prefix="/imports")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_imports(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    imports = (
        db.query(Import)
        .join(Bank)
        .order_by(Import.imported_at.desc())
        .limit(100)
        .all()
    )
    banks = db.query(Bank).filter_by(active=True).order_by(Bank.name).all()
    return templates.TemplateResponse(
        "imports.html",
        {"request": request, "user": current_user, "imports": imports, "banks": banks},
    )


@router.post("/upload")
async def upload_import(
    request: Request,
    bank_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    bank = db.get(Bank, bank_id)
    if not bank:
        return RedirectResponse("/imports?error=bank_not_found", status_code=302)

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    duplicate = db.query(Import).filter(
        Import.bank_id == bank_id,
        (Import.filename == file.filename) | (Import.file_hash == file_hash),
    ).first()
    if duplicate:
        return RedirectResponse("/imports?status=duplicate", status_code=302)

    result = import_file(
        db=db,
        bank=bank,
        filename=file.filename,
        content=content,
        user_id=current_user.id,
        fx_strategy=settings.fx_strategy,
        file_hash=file_hash,
    )

    status_param = "ok" if result.success else "error"
    return RedirectResponse(f"/imports?status={status_param}&rows={result.row_count}", status_code=302)
