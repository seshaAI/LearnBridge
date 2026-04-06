"""Models package — imports all models so Base.metadata sees them."""

from models.user import User
from models.course import Course, Enrollment, CourseRepresentative
from models.lesson import Lesson
from models.quiz import Quiz, QuizAttempt, FinalQuiz, FinalQuizAttempt
from models.points import Points, VideoProgress
from models.message import Message
