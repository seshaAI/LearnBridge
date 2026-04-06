"""
Chat router — messaging system for all users.
Supports teacher↔student, teacher↔teacher, student↔student conversations.
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, case

from database import get_db
from models.user import User
from models.message import Message
from routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])
templates = Jinja2Templates(directory="templates")


def _require_user(request: Request, db: Session = Depends(get_db)):
    """Dependency: any logged-in user."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return user


# ── Inbox ─────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def inbox(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
):
    # Get distinct conversation partners
    conversations = []
    partner_ids = set()

    # All messages involving this user
    msgs = (
        db.query(Message)
        .filter(or_(Message.sender_id == user.id, Message.recipient_id == user.id))
        .order_by(Message.created_at.desc())
        .all()
    )

    for msg in msgs:
        partner_id = msg.recipient_id if msg.sender_id == user.id else msg.sender_id
        if partner_id not in partner_ids:
            partner_ids.add(partner_id)
            partner = db.query(User).filter(User.id == partner_id).first()
            unread = db.query(Message).filter(
                Message.sender_id == partner_id,
                Message.recipient_id == user.id,
                Message.is_read == False,
            ).count()
            conversations.append({
                "partner": partner,
                "last_message": msg.content[:80],
                "last_time": msg.created_at,
                "unread": unread,
                "is_mine": msg.sender_id == user.id,
            })

    # All users (for "new chat" functionality)
    all_users = db.query(User).filter(User.id != user.id).order_by(User.name).all()

    return templates.TemplateResponse(request, "chat_inbox.html", {
        "user": user,
        "conversations": conversations,
        "all_users": all_users,
    })


# ── Chat Thread ───────────────────────────────────────────────────────

@router.get("/{partner_id}", response_class=HTMLResponse)
async def chat_thread(
    partner_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
):
    partner = db.query(User).filter(User.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="User not found")

    # Mark messages as read
    db.query(Message).filter(
        Message.sender_id == partner_id,
        Message.recipient_id == user.id,
        Message.is_read == False,
    ).update({"is_read": True})
    db.commit()

    # Get messages between the two
    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == user.id, Message.recipient_id == partner_id),
                and_(Message.sender_id == partner_id, Message.recipient_id == user.id),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    return templates.TemplateResponse(request, "chat_thread.html", {
        "user": user,
        "partner": partner,
        "messages": messages,
    })


# ── Send Message (AJAX) ──────────────────────────────────────────────

@router.post("/{partner_id}")
async def send_message(
    partner_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
):
    body = await request.json()
    content = body.get("content", "").strip()
    if not content:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    msg = Message(sender_id=user.id, recipient_id=partner_id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return JSONResponse({
        "status": "sent",
        "id": msg.id,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    })


# ── Unread Count (AJAX for nav badge) ────────────────────────────────

@router.get("/api/unread", response_class=JSONResponse)
async def unread_count(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
):
    count = db.query(Message).filter(
        Message.recipient_id == user.id,
        Message.is_read == False,
    ).count()
    return JSONResponse({"unread": count})
