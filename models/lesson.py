"""
Lesson model — each lesson belongs to a course and contains a video URL.
Supports YouTube, Vimeo, direct MP4 links, or raw embed HTML.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    video_url = Column(String(500), nullable=False)
    video_type = Column(String(20), default="youtube")  # youtube | vimeo | direct | embed
    order = Column(Integer, default=0)
