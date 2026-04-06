"""
Message model — stores direct messages between any two users
(teacher↔student, teacher↔teacher, student↔student).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, DateTime
from database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
