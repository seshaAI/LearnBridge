"""
Pydantic schemas for course creation and updates.
"""

from pydantic import BaseModel
from typing import Optional


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = ""


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
