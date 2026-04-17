from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import hash_password, require_admin

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("/users", response_class=HTMLResponse)
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.username).all()
    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "user": current_user, "users": users},
    )


@router.post("/users/new")
def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("viewer"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    db.add(User(
        username=username, email=email,
        password_hash=hash_password(password), role=role,
    ))
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/toggle")
def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    u = db.get(User, user_id)
    if u and u.id != current_user.id:
        u.active = not u.active
        db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    u = db.get(User, user_id)
    if u:
        u.password_hash = hash_password(new_password)
        db.commit()
    return RedirectResponse("/admin/users", status_code=302)
