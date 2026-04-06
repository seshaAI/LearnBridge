from database import SessionLocal, engine, Base
import models
from models import User, Course, Lesson, Quiz, FinalQuiz
from models.user import UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    db = SessionLocal()
    
    # Check if we already seeded to avoid duplicates
    if db.query(User).count() > 0:
        print("Database already has data. Skipping seed to prevent duplicates.")
        db.close()
        return

    print("Seeding database with fake data...")
    hashed_pwd = pwd_context.hash('password123')
    
    # 0. Create Global Admin
    admin_user = User(name="Global Administrator", email="admin@learnbridge.com", password_hash=hashed_pwd, role=UserRole.ADMIN)
    db.add(admin_user)
    db.commit()
    
    # 1. Create Teachers
    teachers = []
    teacher_data = [
        ("Ada Lovelace", "python@learnbridge.com", UserRole.TEACHER),
        ("Warren Buffett", "finance@learnbridge.com", UserRole.TEACHER),
        ("Alan Turing", "maths@learnbridge.com", UserRole.TEACHER),
        ("Dr. Smith", "smith@learnbridge.com", UserRole.TEACHER)
    ]
    for name, email, role in teacher_data:
        t = User(name=name, email=email, password_hash=hashed_pwd, role=role)
        db.add(t)
        teachers.append(t)
        
    # 2. Create Students
    for i in range(1, 11):
        s = User(name=f"Student {i}", email=f"student{i}@learnbridge.com", password_hash=hashed_pwd, role=UserRole.STUDENT)
        db.add(s)
    
    db.commit()
    
    t_python, t_finance, t_maths, t_gen = teachers

    # 3. Create Courses
    # Course 1: Python
    c_python = Course(title="Python for Beginners", description="Learn the basics of Python programming.", teacher_id=t_python.id, is_published=True)
    db.add(c_python)
    db.commit()
    
    l_python1 = Lesson(title="Intro to Python", video_url="https://www.youtube.com/watch?v=kqtD5dpn9C8", video_type="youtube", course_id=c_python.id, order=1)
    db.add(l_python1)
    db.commit()
    
    q_python1 = Quiz(question="What is print() used for?", options=["Outputting data", "Inputting data", "Deleting data", "Nothing"], correct_answer=0, points=20, lesson_id=l_python1.id)
    db.add(q_python1)
    
    fq_python = FinalQuiz(course_id=c_python.id, title="Python Final Exam", passing_score=50, created_by=admin_user.id, questions=[
        {"question": "How do you comment in Python?", "options": ["//", "/*", "#", "--"], "correct_answer": 2, "points": 50},
        {"question": "Which of these is a list?", "options": ["{}", "()", "[]", "<>"], "correct_answer": 2, "points": 50}
    ])
    db.add(fq_python)
    
    # Course 2: Finance
    c_finance = Course(title="Financial Freedom 101", description="Learn how to manage your money effectively and build wealth.", teacher_id=t_finance.id, is_published=True)
    db.add(c_finance)
    db.commit()
    
    l_finance1 = Lesson(title="Budgeting Basics", video_url="https://www.youtube.com/watch?v=sVKQn2I4rqI", video_type="youtube", course_id=c_finance.id, order=1)
    db.add(l_finance1)
    db.commit()
    
    fq_finance = FinalQuiz(course_id=c_finance.id, title="Finance Final Exam", passing_score=100, created_by=admin_user.id, questions=[
        {"question": "What is the primary purpose of a budget?", "options": ["A plan for eating", "A plan for spending and saving", "A bank description", "A type of loan"], "correct_answer": 1, "points": 100}
    ])
    db.add(fq_finance)
    
    # Course 3: Maths
    c_maths = Course(title="Mastering Calculus", description="Derivatives and integrals made easy for everyone.", teacher_id=t_maths.id, is_published=True)
    db.add(c_maths)
    db.commit()
    
    l_maths1 = Lesson(title="What is a Derivative?", video_url="https://www.youtube.com/watch?v=rAof9Ld5sOg", video_type="youtube", course_id=c_maths.id, order=1)
    db.add(l_maths1)
    db.commit()
    
    fq_maths = FinalQuiz(course_id=c_maths.id, title="Calculus Final Exam", passing_score=100, created_by=admin_user.id, questions=[
        {"question": "What is the derivative of x^2?", "options": ["x", "2x", "x^3/3", "1"], "correct_answer": 1, "points": 100}
    ])
    db.add(fq_maths)
    
    db.commit()
    db.close()
    print("✅ Database seeded successfully with 4 Teachers, 10 Students, and 3 Courses!")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed()
