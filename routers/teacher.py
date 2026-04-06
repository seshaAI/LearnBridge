"""
Teacher router — dashboard, course/lesson/quiz CRUD, final quiz management,
student progress, teacher enrollment in other courses, representative appointment.
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, File, UploadFile
import os
import shutil
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user import User, UserRole
from models.course import Course, Enrollment, CourseRepresentative
from models.lesson import Lesson
from models.quiz import Quiz, QuizAttempt, FinalQuiz, FinalQuizAttempt
from models.points import Points, VideoProgress
from routers.auth import get_current_user

router = APIRouter(prefix="/teacher", tags=["teacher"])
templates = Jinja2Templates(directory="templates")


def _require_teacher(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    if user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Teachers only")
    return user


# ── Helpers ───────────────────────────────────────────────────────────

def _detect_video_type(url: str) -> str:
    if not url:
        return "direct"
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "vimeo.com" in url_lower:
        return "vimeo"
    if "<iframe" in url_lower or "<embed" in url_lower:
        return "embed"
    return "direct"


# ── Dashboard ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    total_courses = db.query(Course).filter(Course.teacher_id == user.id).count()
    total_students = (
        db.query(func.count(func.distinct(Enrollment.student_id)))
        .join(Course, Course.id == Enrollment.course_id)
        .filter(Course.teacher_id == user.id)
        .scalar()
    ) or 0
    total_lessons = (
        db.query(Lesson)
        .join(Course, Course.id == Lesson.course_id)
        .filter(Course.teacher_id == user.id)
        .count()
    )
    total_completions = (
        db.query(VideoProgress)
        .join(Lesson, Lesson.id == VideoProgress.lesson_id)
        .join(Course, Course.id == Lesson.course_id)
        .filter(Course.teacher_id == user.id, VideoProgress.watched == True)
        .count()
    )

    courses = (
        db.query(Course)
        .filter(Course.teacher_id == user.id)
        .order_by(Course.created_at.desc())
        .limit(5)
        .all()
    )

    leaderboard = (
        db.query(User.name, Points.total_points)
        .join(Points, Points.student_id == User.id)
        .order_by(Points.total_points.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(request, "teacher_dashboard.html", {
        "user": user,
        "total_courses": total_courses,
        "total_students": total_students,
        "total_lessons": total_lessons,
        "total_completions": total_completions,
        "courses": courses,
        "leaderboard": leaderboard,
    })


# ── Course CRUD ───────────────────────────────────────────────────────

@router.get("/courses", response_class=HTMLResponse)
async def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    courses = (
        db.query(Course)
        .filter(Course.teacher_id == user.id)
        .order_by(Course.created_at.desc())
        .all()
    )
    for c in courses:
        c.lesson_count = db.query(Lesson).filter(Lesson.course_id == c.id).count()
        c.student_count = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        c.has_final_quiz = db.query(FinalQuiz).filter(FinalQuiz.course_id == c.id).first() is not None

    return templates.TemplateResponse(request, "course_manage.html", {
        "user": user, "courses": courses
    })


@router.post("/courses")
async def create_course(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = Course(title=title, description=description, teacher_id=user.id)
    db.add(course)
    db.commit()
    return RedirectResponse("/teacher/courses", status_code=303)


@router.get("/courses/{course_id}", response_class=HTMLResponse)
async def view_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .order_by(Lesson.order)
        .all()
    )
    for lesson in lessons:
        lesson.quizzes = db.query(Quiz).filter(Quiz.lesson_id == lesson.id).all()

    enrolled_students = (
        db.query(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .filter(Enrollment.course_id == course_id)
        .all()
    )

    final_quiz = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()

    reps = (
        db.query(User)
        .join(CourseRepresentative, CourseRepresentative.user_id == User.id)
        .filter(CourseRepresentative.course_id == course_id)
        .all()
    )

    # All teachers for representative selection
    all_teachers = (
        db.query(User)
        .filter(User.role == UserRole.TEACHER, User.id != user.id)
        .all()
    )

    return templates.TemplateResponse(request, "course_detail_teacher.html", {
        "user": user,
        "course": course,
        "lessons": lessons,
        "enrolled_students": enrolled_students,
        "final_quiz": final_quiz,
        "representatives": reps,
        "all_teachers": all_teachers,
    })


@router.post("/courses/{course_id}/update")
async def update_course(
    course_id: int,
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.title = title
    course.description = description
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


@router.post("/courses/{course_id}/delete")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Gather IDs for safer child-first deletion
    lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
    if lessons:
        lesson_ids = [l.id for l in lessons]
        # 1. Video Progress
        db.query(VideoProgress).filter(VideoProgress.lesson_id.in_(lesson_ids)).delete(synchronize_session=False)
        # 2. Quiz Attempts
        db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id.in_(
                db.query(Quiz.id).filter(Quiz.lesson_id.in_(lesson_ids))
            )
        ).delete(synchronize_session=False)
        # 3. Quizzes
        db.query(Quiz).filter(Quiz.lesson_id.in_(lesson_ids)).delete(synchronize_session=False)
        # 4. Lessons
        db.query(Lesson).filter(Lesson.course_id == course_id).delete(synchronize_session=False)

    # 5. Final Quiz Attempts
    fq = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()
    if fq:
        db.query(FinalQuizAttempt).filter(FinalQuizAttempt.final_quiz_id == fq.id).delete(synchronize_session=False)
        # 6. Final Quiz
        db.delete(fq)

    # 7. Enrollments & Reps
    db.query(Enrollment).filter(Enrollment.course_id == course_id).delete(synchronize_session=False)
    db.query(CourseRepresentative).filter(CourseRepresentative.course_id == course_id).delete(synchronize_session=False)
    
    # 8. Course
    db.delete(course)
    db.commit()
    return RedirectResponse("/teacher/courses", status_code=303)


# ── Lesson CRUD ───────────────────────────────────────────────────────

@router.post("/courses/{course_id}/lessons")
async def add_lesson(
    course_id: int,
    title: str = Form(...),
    video_url: str = Form(""),
    video_file: UploadFile = File(None),
    order: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    final_url = video_url
    if video_file and video_file.filename:
        os.makedirs("static/uploads", exist_ok=True)
        # Using a safer filename logic simply by prepending course_id
        safe_filename = f"{course_id}_{video_file.filename.replace(' ', '_')}"
        file_path = os.path.join("static", "uploads", safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        final_url = f"/static/uploads/{safe_filename}"

    video_type = "direct" if (video_file and video_file.filename) else _detect_video_type(final_url)
    lesson = Lesson(course_id=course_id, title=title, video_url=final_url,
                    video_type=video_type, order=order)
    db.add(lesson)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


@router.post("/lessons/{lesson_id}/update")
async def update_lesson(
    lesson_id: int,
    title: str = Form(...),
    video_url: str = Form(""),
    video_file: UploadFile = File(None),
    order: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    course = db.query(Course).filter(Course.id == lesson.course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Not your course")

    final_url = video_url
    if video_file and video_file.filename:
        os.makedirs("static/uploads", exist_ok=True)
        safe_filename = f"{lesson.course_id}_{video_file.filename.replace(' ', '_')}"
        file_path = os.path.join("static", "uploads", safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        final_url = f"/static/uploads/{safe_filename}"

    lesson.title = title
    if final_url:
        lesson.video_url = final_url
        lesson.video_type = "direct" if (video_file and video_file.filename) else _detect_video_type(final_url)
    lesson.order = order
    db.commit()
    return RedirectResponse(f"/teacher/courses/{lesson.course_id}", status_code=303)


@router.post("/lessons/{lesson_id}/delete")
async def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    course = db.query(Course).filter(Course.id == lesson.course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Not your course")

    course_id = lesson.course_id
    db.query(Quiz).filter(Quiz.lesson_id == lesson_id).delete()
    db.query(VideoProgress).filter(VideoProgress.lesson_id == lesson_id).delete()
    db.delete(lesson)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


# ── Per-Lesson Quiz CRUD ─────────────────────────────────────────────

@router.post("/lessons/{lesson_id}/quizzes")
async def add_quiz(
    lesson_id: int,
    question: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct_answer: int = Form(...),
    points: int = Form(20),
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    course = db.query(Course).filter(Course.id == lesson.course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Not your course")

    quiz = Quiz(
        lesson_id=lesson_id,
        question=question,
        options=[option_a, option_b, option_c, option_d],
        correct_answer=correct_answer,
        points=points,
    )
    db.add(quiz)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{lesson.course_id}", status_code=303)


@router.post("/quizzes/{quiz_id}/delete")
async def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    lesson = db.query(Lesson).filter(Lesson.id == quiz.lesson_id).first()
    course = db.query(Course).filter(Course.id == lesson.course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Not your course")

    course_id = lesson.course_id
    db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).delete()
    db.delete(quiz)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


# ── Final Quiz Management ────────────────────────────────────────────

@router.get("/courses/{course_id}/final-quiz", response_class=HTMLResponse)
async def final_quiz_page(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    final_quiz = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()

    return templates.TemplateResponse(request, "final_quiz_manage.html", {
        "user": user,
        "course": course,
        "final_quiz": final_quiz,
    })


@router.post("/courses/{course_id}/final-quiz")
async def save_final_quiz(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    body = await request.json()
    questions = body.get("questions", [])
    title = body.get("title", "Final Exam")
    passing_score = body.get("passing_score", 60)

    if len(questions) < 1:
        return JSONResponse({"error": "At least 1 question required"}, status_code=400)

    existing = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()
    if existing:
        existing.title = title
        existing.questions = questions
        existing.passing_score = passing_score
    else:
        fq = FinalQuiz(
            course_id=course_id,
            title=title,
            questions=questions,
            passing_score=passing_score,
            created_by=user.id,
        )
        db.add(fq)

    # Mark course as published
    course.is_published = 1
    db.commit()

    return JSONResponse({"status": "saved"})


# ── Teacher Enrollment (browse other courses) ────────────────────────

@router.get("/browse", response_class=HTMLResponse)
async def browse_all_courses(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    courses = (
        db.query(Course)
        .filter(Course.teacher_id != user.id)
        .order_by(Course.created_at.desc())
        .all()
    )
    enrolled_ids = {
        e.course_id
        for e in db.query(Enrollment).filter(Enrollment.student_id == user.id).all()
    }
    for c in courses:
        c.is_enrolled = c.id in enrolled_ids
        c.lesson_count = db.query(Lesson).filter(Lesson.course_id == c.id).count()
        c.student_count = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        c.teacher_name = db.query(User.name).filter(User.id == c.teacher_id).scalar()

    return templates.TemplateResponse(request, "course_browse.html", {
        "user": user, "courses": courses, "enrolled_ids": enrolled_ids,
    })


@router.post("/courses/{course_id}/enroll")
async def teacher_enroll(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    existing = db.query(Enrollment).filter(
        Enrollment.student_id == user.id, Enrollment.course_id == course_id
    ).first()
    if not existing:
        db.add(Enrollment(student_id=user.id, course_id=course_id))
        db.commit()
    return RedirectResponse(f"/teacher/browse", status_code=303)


# ── Appoint Representative ───────────────────────────────────────────

@router.post("/courses/{course_id}/representative")
async def appoint_representative(
    course_id: int,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = db.query(CourseRepresentative).filter(
        CourseRepresentative.course_id == course_id,
        CourseRepresentative.user_id == user_id,
    ).first()
    if not existing:
        db.add(CourseRepresentative(
            course_id=course_id, user_id=user_id, appointed_by=user.id
        ))
        db.commit()

    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


@router.post("/courses/{course_id}/representative/{rep_id}/remove")
async def remove_representative(
    course_id: int,
    rep_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    db.query(CourseRepresentative).filter(
        CourseRepresentative.course_id == course_id,
        CourseRepresentative.user_id == rep_id,
    ).delete()
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


# ── Student Progress ─────────────────────────────────────────────────

@router.get("/students", response_class=HTMLResponse)
async def student_progress(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_teacher),
):
    students = (
        db.query(User.id, User.name, User.email, Points.total_points)
        .join(Enrollment, Enrollment.student_id == User.id)
        .join(Course, Course.id == Enrollment.course_id)
        .outerjoin(Points, Points.student_id == User.id)
        .filter(Course.teacher_id == user.id)
        .group_by(User.id, User.name, User.email, Points.total_points)
        .order_by(Points.total_points.desc())
        .all()
    )

    return templates.TemplateResponse(request, "student_progress.html", {
        "user": user, "students": students
    })
