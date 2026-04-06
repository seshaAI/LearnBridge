"""
reset_db.py — Forcefully Drop & Recreate All Tables
===================================================
Run this ONLY when the cloud database schema is corrupted or missing columns.
It uses the DATABASE_URL from .env.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from database import engine, Base
import models  # import all models to register them with Base.metadata

def reset():
    print(f"🔥 Attempting to reset database: {os.getenv('DATABASE_URL')[:20]}...")
    
    # Drop all tables
    print("🗑️ Dropping all existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    # Recreate all tables
    print("🏗️ Recreating all tables from models...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database reset successfully. You should run seed_db.py next.")

if __name__ == "__main__":
    reset()
