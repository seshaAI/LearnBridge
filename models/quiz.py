"""
Quiz models — per-lesson quizzes and course-level final quizzes.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from database import Base


class Quiz(Base):
    """Per-lesson quiz question (inline quizzes during course)."""
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    question = Column(String(500), nullable=False)
    options = Column(JSON, nullable=False)           # ["A", "B", "C", "D"]
    correct_answer = Column(Integer, nullable=False)  # 0-based index
    points = Column(Integer, default=20)              # teacher-configurable points


class QuizAttempt(Base):
    """Tracks per-lesson quiz attempts by students."""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    selected_answer = Column(Integer, nullable=False)
    is_correct = Column(Boolean, default=False)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FinalQuiz(Base):
    """Course-level final quiz that students must pass to complete a course."""
    __tablename__ = "final_quizzes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, unique=True)
    title = Column(String(255), default="Final Exam")
    questions = Column(JSON, nullable=False)  # [{question, options, correct_answer, points}, ...]
    passing_score = Column(Integer, default=60)  # percentage
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FinalQuizAttempt(Base):
    """Tracks student attempts at a course's final quiz."""
    __tablename__ = "final_quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    final_quiz_id = Column(Integer, ForeignKey("final_quizzes.id"), nullable=False)
    score = Column(Integer, default=0)  # percentage
    points_earned = Column(Integer, default=0)
    passed = Column(Boolean, default=False)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
