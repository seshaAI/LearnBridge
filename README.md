# 🎓 LearnBridge LMS

LearnBridge is a modern, gamified Learning Management System (LMS) designed for the next generation of online education. It features a stunning, theme-based UI, professional teacher/student role separation, and a global **Observer Deck** for administrative power.

---

## 🌟 Key Features

### 🎨 Premium Dynamic Themes
LearnBridge isn't just a platform; it's an experience. Users can toggle between **Dark**, **Light**, and **Aqua Depth** themes, with every setting persisted flawlessly across sessions.

### 💂‍♂️ Global Admin Observer Deck
The centerpiece of platform management. Admins get total oversight of every user and course, with built-in:
- **Real-time Metrics:** Tracking teachers, students, and global enrollments.
- **Direct Messaging:** Jump directly into private chats with any user.
- **Session Control:** Instant CRUD operations (Create, Read, Update, Delete) to maintain platform quality.

### 🕹️ Gamified Education
Students earn **Points** and **Badges** for progress, visible on a global **Leaderboard** to encourage competitive learning.

### ⚡ Technical Excellence
- **Cloud Database:** Integrated with **Supabase PostgreSQL** for secure, high-scale storage.
- **Modern Backend:** Powered by **FastAPI** for ultra-fast, asynchronous performance.
- **Seamless Chat:** A custom-built messaging architecture for instant Teacher-Student feedback.

---

## 🚀 Live Deployment (Render & Supabase)

LearnBridge is optimized for immediate cloud deployment. Follow these 3 steps to go live:

1.  **Preparation:** Ensure your **Supabase** database is running and you have your `DATABASE_URL` ready.
2.  **Deployment:** Create a free account at [Render.com](https://render.com).
3.  **One-Click:** Click **"New"** -> **"Blueprint"** and connect your GitHub repository.

Render will automatically read the `render.yaml` file, install your dependencies, and launch your LMS at a public URL (e.g., `https://learnbridge-lms.onrender.com`).

> [!NOTE]
> Make sure to add your `DATABASE_URL` to the **Environment Variables** in the Render dashboard during the Blueprint setup!

---

## 🛠️ Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/seshaAI/LearnBridge.git
cd LearnBridge
```

### 2. Environment Configuration
Copy the template and plug in your database credentials:
```bash
cp .env.example .env
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed and Launch
Initialize your database with professional demo data:
```bash
python seed_db.py
python main.py
```

---

## 🛠️ Deploy to the Cloud
LearnBridge is production-ready. You can deploy it to **Render**, **Railway**, or **Vercel** with minimal configuration:

1.  **Database:** Provision a **Supabase** PostgreSQL instance.
2.  **Host:** Link your GitHub repository.
3.  **Command:** Use `uvicorn main:app --host 0.0.0.0 --port 8000`.

---

## 🤝 Contribution
Contributions are welcome! Feel free to open issues or submit pull requests to make LearnBridge better.

## 📄 License
This project is licensed under the **MIT License**.
