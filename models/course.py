"""
Course, Enrollment, and CourseRepresentative models.
Teachers create courses; users enroll; teachers can appoint representatives.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_published = Column(Boolean, default=False)  # has final quiz, ready for students
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    completed = Column(Boolean, default=False)  # passed final quiz
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CourseRepresentative(Base):
    """A user appointed by the course teacher to help manage content."""
    __tablename__ = "course_representatives"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
