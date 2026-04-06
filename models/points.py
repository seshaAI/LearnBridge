"""
Points and VideoProgress models.
Tracks student gamification state (total points, badges) and per-video watch status.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, JSON
from database import Base


class Points(Base):
    """Aggregate table for a student's total points and earned badges."""
    __tablename__ = "points"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    total_points = Column(Integer, default=0)
    badges = Column(JSON, default=list)  # e.g. ["First Steps", "Quiz Whiz"]


class VideoProgress(Base):
    """Tracks whether a student has watched a specific lesson video."""
    __tablename__ = "video_progress"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    watched = Column(Boolean, default=False)
    watched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
