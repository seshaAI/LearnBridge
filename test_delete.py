from database import SessionLocal
from routers.teacher import delete_course
from models.course import Course
import asyncio
from fastapi import Request

async def test():
    db = SessionLocal()
    # Find course 1
    course = db.query(Course).first()
    if not course:
        print("No course found!")
        return
    print(f"Trying to delete course {course.id}")
    
    # We can't call the FastAPI endpoint directly easily because of Depends, so let's just copy the logic to test it.
    course_id = course.id
    try:
        from models import Lesson, Quiz, FinalQuiz, FinalQuizAttempt, Enrollment, CourseRepresentative
        from models.points import VideoProgress
        from models.quiz import QuizAttempt
        
        lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
        if lessons:
            lesson_ids = [l.id for l in lessons]
            db.query(VideoProgress).filter(VideoProgress.lesson_id.in_(lesson_ids)).delete(synchronize_session=False)
            db.query(QuizAttempt).filter(
                QuizAttempt.quiz_id.in_(
                    db.query(Quiz.id).filter(Quiz.lesson_id.in_(lesson_ids))
                )
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
        db.commit()
        print("Success!")
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
