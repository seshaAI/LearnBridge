"""
Pydantic schemas for lesson and quiz validation.
"""

from pydantic import BaseModel
from typing import List, Optional


class LessonCreate(BaseModel):
    title: str
    youtube_url: str
    order: Optional[int] = 0


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    youtube_url: Optional[str] = None
    order: Optional[int] = None


class QuizCreate(BaseModel):
    question: str
    options: List[str]       # e.g. ["Paris", "London", "Berlin", "Rome"]
    correct_answer: int      # 0-based index


class QuizAnswer(BaseModel):
    selected_answer: int     # 0-based index
