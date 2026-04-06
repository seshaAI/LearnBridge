"""
Authentication router — register, login, logout, profile editing.
Uses JWT tokens stored in HTTP-only cookies for session management.
"""

import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from database import get_db
from models.user import User, UserRole
from models.points import Points

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")

# ── Password hashing ─────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── JWT config ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None


# ── Pages ─────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        if user.role == UserRole.TEACHER:
            return RedirectResponse("/teacher/dashboard", status_code=303)
        return RedirectResponse("/student/dashboard", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


# ── Register ──────────────────────────────────────────────────────────

@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            request, "register.html", {"error": "Email already registered."}
        )

    user = User(
        name=name,
        email=email,
        password_hash=pwd_context.hash(password),
        role=UserRole(role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-create a Points row for students
    if user.role == UserRole.STUDENT:
        db.add(Points(student_id=user.id, total_points=0, badges=[]))
        db.commit()

    return RedirectResponse("/auth/login?registered=1", status_code=303)


# ── Login ─────────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password."}
        )

    token = create_access_token({"user_id": user.id, "role": user.role.value})
    redirect_url = (
        "/teacher/dashboard" if user.role == UserRole.TEACHER else "/student/dashboard"
    )
    response = RedirectResponse(redirect_url, status_code=303)
    response.set_cookie(
        key="access_token", value=token, httponly=True,
        max_age=EXPIRE_MINUTES * 60, samesite="lax",
    )
    return response


# ── Logout ────────────────────────────────────────────────────────────

@router.get("/logout")
async def logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response


# ── Settings / Profile Edit ───────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    return templates.TemplateResponse(request, "settings.html", {
        "user": user, "success": None, "error": None,
    })


@router.post("/settings")
async def update_profile(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    current_password: str = Form(""),
    new_password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    # Check if email changed and already taken
    if email != user.email:
        existing = db.query(User).filter(User.email == email, User.id != user.id).first()
        if existing:
            return templates.TemplateResponse(request, "settings.html", {
                "user": user, "success": None,
                "error": "That email is already taken by another account.",
            })

    user.name = name
    user.email = email

    # Update password if provided
    if new_password:
        if not current_password or not pwd_context.verify(current_password, user.password_hash):
            return templates.TemplateResponse(request, "settings.html", {
                "user": user, "success": None,
                "error": "Current password is incorrect.",
            })
        user.password_hash = pwd_context.hash(new_password)

    db.commit()

    # Refresh JWT with new data
    token = create_access_token({"user_id": user.id, "role": user.role.value})
    response = RedirectResponse("/auth/settings?saved=1", status_code=303)
    response.set_cookie(
        key="access_token", value=token, httponly=True,
        max_age=EXPIRE_MINUTES * 60, samesite="lax",
    )
    return response
