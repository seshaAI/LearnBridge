"""
LearnBridge LMS — Main Application Entry Point
=================================================
Assembles the FastAPI application, mounts static files,
registers routers, and creates database tables on startup.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from database import engine, Base

# Import all models so Base.metadata registers them
import models  # noqa: F401

from routers import auth, teacher, student, chat

# ── Create App ───────────────────────────────────────────────────

app = FastAPI(
    title="LearnBridge LMS",
    description="A modern Learning Management System with gamification",
    version="2.0.0",
)

# ── Mount static files ───────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Register routers ────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(chat.router)

# ── Create tables on startup ────────────────────────────────────

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print("✅ LearnBridge — Database tables created / verified.")


# ── Root redirect ────────────────────────────────────────────────

@app.get("/")
async def root(request: Request):
    return RedirectResponse("/auth/login", status_code=303)


# ── Custom 403 handler as redirect ──────────────────────────────

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return RedirectResponse("/auth/login", status_code=303)


# ── Run with uvicorn ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
