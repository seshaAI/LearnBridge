from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user import User, UserRole
from models.course import Course, Enrollment, CourseRepresentative
from models.lesson import Lesson
from models.quiz import Quiz, QuizAttempt, FinalQuiz, FinalQuizAttempt
from models.points import VideoProgress, Points
from models.message import Message
from routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

def _require_admin(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admins only")
    return user

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_admin),
):
    # Global Metrics
    total_teachers = db.query(User).filter(User.role == UserRole.TEACHER).count()
    total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    total_courses = db.query(Course).count()
    total_enrollments = db.query(Enrollment).count()
    
    # Detailed Data
    platform_users = db.query(User).filter(User.role != UserRole.ADMIN).order_by(User.role.desc(), User.name).all()
    courses = db.query(Course).order_by(Course.created_at.desc()).all()
    
    for c in courses:
        c.student_count = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        teacher = db.query(User).filter(User.id == c.teacher_id).first()
        c.teacher_name = teacher.name if teacher else "Unknown"

    return templates.TemplateResponse(request, "admin_dashboard.html", {
        "user": user,
        "total_teachers": total_teachers,
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "platform_users": platform_users,
        "courses": courses
    })

def _admin_delete_course(course_id: int, db: Session):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course: return
    lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
    if lessons:
        lesson_ids = [l.id for l in lessons]
        db.query(VideoProgress).filter(VideoProgress.lesson_id.in_(lesson_ids)).delete(synchronize_session=False)
        db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id.in_(db.query(Quiz.id).filter(Quiz.lesson_id.in_(lesson_ids)))
        ).delete(synchronize_session=False)
        db.query(Quiz).filter(Quiz.lesson_id.in_(lesson_ids)).delete(synchronize_session=False)
        db.query(Lesson).filter(Lesson.course_id == course_id).delete(synchronize_session=False)

    fq = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()
    if fq:
        db.query(FinalQuizAttempt).filter(FinalQuizAttempt.final_quiz_id == fq.id).delete(synchronize_session=False)
        db.delete(fq)

    db.query(Enrollment).filter(Enrollment.course_id == course_id).delete(synchronize_session=False)
    db.query(CourseRepresentative).filter(CourseRepresentative.course_id == course_id).delete(synchronize_session=False)
    db.delete(course)

@router.post("/courses/{course_id}/delete")
async def admin_delete_course_route(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_admin)
):
    _admin_delete_course(course_id, db)
    db.commit()
    return RedirectResponse("/admin/dashboard", status_code=303)

@router.post("/users/{user_id}/delete")
async def admin_delete_user_route(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_admin)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user or target_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete admin or non-existent user")
    
    # 1. Delete Messages
    db.query(Message).filter(
        (Message.sender_id == user_id) | (Message.recipient_id == user_id)
    ).delete(synchronize_session=False)
    
    # 2. Delete Student Data
    if target_user.role == UserRole.STUDENT:
        db.query(Enrollment).filter(Enrollment.student_id == user_id).delete(synchronize_session=False)
        db.query(CourseRepresentative).filter(CourseRepresentative.user_id == user_id).delete(synchronize_session=False)
        db.query(VideoProgress).filter(VideoProgress.student_id == user_id).delete(synchronize_session=False)
        db.query(QuizAttempt).filter(QuizAttempt.student_id == user_id).delete(synchronize_session=False)
        db.query(FinalQuizAttempt).filter(FinalQuizAttempt.student_id == user_id).delete(synchronize_session=False)
        db.query(Points).filter(Points.student_id == user_id).delete(synchronize_session=False)

    # 3. Delete Teacher Data
    if target_user.role == UserRole.TEACHER:
        teacher_courses = db.query(Course).filter(Course.teacher_id == user_id).all()
        for tc in teacher_courses:
            _admin_delete_course(tc.id, db)
            
    db.delete(target_user)
    db.commit()
    return RedirectResponse("/admin/dashboard", status_code=303)
