"""
Student router — dashboard, course browsing, enrollment, video watching,
quiz submission, final quiz, gamification, leaderboard, and profile.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, UserRole
from models.course import Course, Enrollment
from models.lesson import Lesson
from models.quiz import Quiz, QuizAttempt, FinalQuiz, FinalQuizAttempt
from models.points import Points, VideoProgress
from routers.auth import get_current_user

router = APIRouter(prefix="/student", tags=["student"])
templates = Jinja2Templates(directory="templates")


# ── Badge definitions ─────────────────────────────────────────────────
BADGE_RULES = {
    "First Steps":    {"type": "videos_watched",    "threshold": 1,   "icon": "🎬", "desc": "Watch your first video"},
    "Curious Mind":   {"type": "enrollments",        "threshold": 3,   "icon": "🧠", "desc": "Enroll in 3 courses"},
    "Video Veteran":  {"type": "videos_watched",    "threshold": 10,  "icon": "🎥", "desc": "Watch 10 videos"},
    "Quiz Whiz":      {"type": "quizzes_completed", "threshold": 5,   "icon": "🧩", "desc": "Complete 5 quizzes"},
    "Scholar":        {"type": "courses_completed", "threshold": 1,   "icon": "🎓", "desc": "Complete a course"},
    "Centurion":      {"type": "points",            "threshold": 100, "icon": "💯", "desc": "Earn 100 points"},
    "Overachiever":   {"type": "points",            "threshold": 500, "icon": "🏆", "desc": "Earn 500 points"},
}


def _require_student(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students only")
    return user


def _check_and_award_badges(student_id: int, db: Session):
    points_row = db.query(Points).filter(Points.student_id == student_id).first()
    if not points_row:
        return

    current_badges = list(points_row.badges or [])

    videos_watched = db.query(VideoProgress).filter(
        VideoProgress.student_id == student_id, VideoProgress.watched == True,
    ).count()
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).count()
    quizzes_completed = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == student_id
    ).count()

    # Count courses completed (passed final quiz)
    courses_completed = db.query(Enrollment).filter(
        Enrollment.student_id == student_id, Enrollment.completed == True
    ).count()

    stats = {
        "videos_watched": videos_watched,
        "enrollments": enrollments,
        "quizzes_completed": quizzes_completed,
        "courses_completed": courses_completed,
        "points": points_row.total_points,
    }

    new_badges = list(current_badges)
    for badge_name, rule in BADGE_RULES.items():
        if badge_name not in new_badges and stats.get(rule["type"], 0) >= rule["threshold"]:
            new_badges.append(badge_name)

    if new_badges != current_badges:
        points_row.badges = new_badges
        db.commit()


# ── Dashboard ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    total_points = points_row.total_points if points_row else 0
    badges = list(points_row.badges or []) if points_row else []

    enrolled = (
        db.query(Course, Enrollment)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.student_id == user.id)
        .all()
    )
    courses_data = []
    for course, enrollment in enrolled:
        total_lessons = db.query(Lesson).filter(Lesson.course_id == course.id).count()
        watched_lessons = (
            db.query(VideoProgress)
            .join(Lesson, Lesson.id == VideoProgress.lesson_id)
            .filter(
                VideoProgress.student_id == user.id,
                Lesson.course_id == course.id,
                VideoProgress.watched == True,
            )
            .count()
        )
        progress = int((watched_lessons / total_lessons * 100) if total_lessons > 0 else 0)
        has_final = db.query(FinalQuiz).filter(FinalQuiz.course_id == course.id).first() is not None
        courses_data.append({
            "course": course,
            "total_lessons": total_lessons,
            "watched_lessons": watched_lessons,
            "progress": progress,
            "completed": enrollment.completed == True,
            "has_final_quiz": has_final,
        })

    rank = db.query(Points).filter(Points.total_points > total_points).count() + 1
    _check_and_award_badges(user.id, db)

    return templates.TemplateResponse(request, "student_dashboard.html", {
        "user": user,
        "total_points": total_points,
        "badges": badges,
        "courses_data": courses_data,
        "rank": rank,
        "badge_rules": BADGE_RULES,
    })


# ── Browse & Enroll ───────────────────────────────────────────────────

@router.get("/courses", response_class=HTMLResponse)
async def browse_courses(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    courses = db.query(Course).order_by(Course.created_at.desc()).all()
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
        "user": user, "courses": courses, "enrolled_ids": enrolled_ids
    })


@router.post("/courses/{course_id}/enroll")
async def enroll(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    existing = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not existing:
        db.add(Enrollment(student_id=user.id, course_id=course_id))
        db.commit()
        _check_and_award_badges(user.id, db)
    return RedirectResponse(f"/student/courses/{course_id}", status_code=303)


# ── Course View ───────────────────────────────────────────────────────

@router.get("/courses/{course_id}", response_class=HTMLResponse)
async def view_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        return RedirectResponse("/student/courses", status_code=303)

    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .order_by(Lesson.order)
        .all()
    )
    for lesson in lessons:
        lesson.watched = (
            db.query(VideoProgress)
            .filter(
                VideoProgress.student_id == user.id,
                VideoProgress.lesson_id == lesson.id,
                VideoProgress.watched == True,
            )
            .first() is not None
        )
        lesson.quizzes = db.query(Quiz).filter(Quiz.lesson_id == lesson.id).all()
        for quiz in lesson.quizzes:
            quiz.attempted = (
                db.query(QuizAttempt)
                .filter(QuizAttempt.student_id == user.id, QuizAttempt.quiz_id == quiz.id)
                .first() is not None
            )

    total_lessons = len(lessons)
    watched_count = sum(1 for l in lessons if l.watched)
    progress = int((watched_count / total_lessons * 100) if total_lessons > 0 else 0)
    course.teacher_name = db.query(User.name).filter(User.id == course.teacher_id).scalar()

    # Final quiz info
    final_quiz = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()
    final_quiz_passed = False
    final_quiz_attempted = False
    if final_quiz:
        attempt = db.query(FinalQuizAttempt).filter(
            FinalQuizAttempt.student_id == user.id,
            FinalQuizAttempt.final_quiz_id == final_quiz.id,
        ).first()
        if attempt:
            final_quiz_attempted = True
            final_quiz_passed = attempt.passed == True

    all_watched = watched_count >= total_lessons and total_lessons > 0

    return templates.TemplateResponse(request, "course_view.html", {
        "user": user,
        "course": course,
        "lessons": lessons,
        "progress": progress,
        "watched_count": watched_count,
        "total_lessons": total_lessons,
        "final_quiz": final_quiz,
        "final_quiz_passed": final_quiz_passed,
        "final_quiz_attempted": final_quiz_attempted,
        "all_watched": all_watched,
        "course_completed": enrollment.completed == True,
    })


# ── Mark Video Watched (AJAX) ─────────────────────────────────────────

@router.post("/lessons/{lesson_id}/watch")
async def mark_watched(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    existing = (
        db.query(VideoProgress)
        .filter(
            VideoProgress.student_id == user.id,
            VideoProgress.lesson_id == lesson_id,
            VideoProgress.watched == True,
        )
        .first()
    )
    if existing:
        return JSONResponse({"status": "already_watched", "points": 0})

    db.add(VideoProgress(student_id=user.id, lesson_id=lesson_id, watched=True))

    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    if points_row:
        points_row.total_points += 10
    else:
        points_row = Points(student_id=user.id, total_points=10, badges=[])
        db.add(points_row)

    db.commit()
    _check_and_award_badges(user.id, db)

    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    return JSONResponse({
        "status": "success", "points": 10,
        "total_points": points_row.total_points,
    })


# ── Submit Per-Lesson Quiz (AJAX) ────────────────────────────────────

@router.post("/quizzes/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    body = await request.json()
    selected_answer = body.get("selected_answer")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    existing = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == user.id, QuizAttempt.quiz_id == quiz_id)
        .first()
    )
    if existing:
        return JSONResponse({
            "status": "already_attempted",
            "is_correct": existing.is_correct,
            "correct_answer": quiz.correct_answer,
            "points": 0,
        })

    is_correct = 1 if selected_answer == quiz.correct_answer else 0
    db.add(QuizAttempt(
        student_id=user.id, quiz_id=quiz_id,
        selected_answer=selected_answer, is_correct=is_correct,
    ))

    points_earned = quiz.points if is_correct else 0
    if points_earned > 0:
        points_row = db.query(Points).filter(Points.student_id == user.id).first()
        if points_row:
            points_row.total_points += points_earned
        else:
            db.add(Points(student_id=user.id, total_points=points_earned, badges=[]))

    db.commit()
    _check_and_award_badges(user.id, db)

    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    return JSONResponse({
        "status": "success",
        "is_correct": is_correct,
        "correct_answer": quiz.correct_answer,
        "points": points_earned,
        "total_points": points_row.total_points if points_row else 0,
    })


# ── Final Quiz ────────────────────────────────────────────────────────

@router.get("/courses/{course_id}/final-quiz", response_class=HTMLResponse)
async def take_final_quiz(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    final_quiz = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()
    if not final_quiz:
        return RedirectResponse(f"/student/courses/{course_id}", status_code=303)

    # Check if already attempted
    attempt = db.query(FinalQuizAttempt).filter(
        FinalQuizAttempt.student_id == user.id,
        FinalQuizAttempt.final_quiz_id == final_quiz.id,
    ).first()

    return templates.TemplateResponse(request, "final_quiz_take.html", {
        "user": user,
        "course": course,
        "final_quiz": final_quiz,
        "previous_attempt": attempt,
    })


@router.post("/courses/{course_id}/final-quiz")
async def submit_final_quiz(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    final_quiz = db.query(FinalQuiz).filter(FinalQuiz.course_id == course_id).first()
    if not final_quiz:
        return JSONResponse({"error": "No final quiz"}, status_code=404)

    # Check if already attempted
    existing = db.query(FinalQuizAttempt).filter(
        FinalQuizAttempt.student_id == user.id,
        FinalQuizAttempt.final_quiz_id == final_quiz.id,
    ).first()
    if existing:
        return JSONResponse({
            "status": "already_attempted",
            "score": existing.score,
            "passed": existing.passed,
        })

    body = await request.json()
    answers = body.get("answers", {})  # {question_index: selected_answer}

    questions = final_quiz.questions
    total_points = 0
    earned_points = 0
    correct_count = 0

    for i, q in enumerate(questions):
        q_points = q.get("points", 10)
        total_points += q_points
        student_answer = answers.get(str(i))
        if student_answer == q["correct_answer"]:
            earned_points += q_points
            correct_count += 1

    score_pct = int((earned_points / total_points * 100) if total_points > 0 else 0)
    passed = 1 if score_pct >= final_quiz.passing_score else 0

    attempt = FinalQuizAttempt(
        student_id=user.id,
        final_quiz_id=final_quiz.id,
        score=score_pct,
        points_earned=earned_points,
        passed=passed,
    )
    db.add(attempt)

    # Award points
    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    if points_row:
        points_row.total_points += earned_points
    else:
        db.add(Points(student_id=user.id, total_points=earned_points, badges=[]))

    # Mark enrollment as completed if passed
    if passed:
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == user.id, Enrollment.course_id == course_id
        ).first()
        if enrollment:
            enrollment.completed = 1

    db.commit()
    _check_and_award_badges(user.id, db)

    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    return JSONResponse({
        "status": "success",
        "score": score_pct,
        "passed": passed,
        "points_earned": earned_points,
        "total_points": points_row.total_points if points_row else 0,
        "correct_count": correct_count,
        "total_questions": len(questions),
    })


# ── Leaderboard ───────────────────────────────────────────────────────

@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    results = (
        db.query(User.id, User.name, Points.total_points, Points.badges)
        .join(Points, Points.student_id == User.id)
        .order_by(Points.total_points.desc())
        .all()
    )

    leaderboard_data = []
    my_points = 0
    my_rank = 0
    for i, (uid, name, pts, badges) in enumerate(results, 1):
        entry = {
            "rank": i, "name": name, "points": pts or 0,
            "badges": list(badges or []), "is_me": uid == user.id,
        }
        leaderboard_data.append(entry)
        if uid == user.id:
            my_points = entry["points"]
            my_rank = i

    return templates.TemplateResponse(request, "leaderboard.html", {
        "user": user,
        "leaderboard": leaderboard_data,
        "my_points": my_points,
        "my_rank": my_rank,
        "badge_rules": BADGE_RULES,
    })


# ── Profile ───────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    _check_and_award_badges(user.id, db)

    points_row = db.query(Points).filter(Points.student_id == user.id).first()
    total_points = points_row.total_points if points_row else 0
    badges = list(points_row.badges or []) if points_row else []

    videos_watched = db.query(VideoProgress).filter(
        VideoProgress.student_id == user.id, VideoProgress.watched == True
    ).count()
    quizzes_completed = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == user.id
    ).count()
    courses_enrolled = db.query(Enrollment).filter(
        Enrollment.student_id == user.id
    ).count()

    rank = db.query(Points).filter(Points.total_points > total_points).count() + 1

    return templates.TemplateResponse(request, "profile.html", {
        "user": user,
        "total_points": total_points,
        "badges": badges,
        "badge_rules": BADGE_RULES,
        "videos_watched": videos_watched,
        "quizzes_completed": quizzes_completed,
        "courses_enrolled": courses_enrolled,
        "rank": rank,
    })
