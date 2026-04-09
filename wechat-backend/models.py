from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    # Timestamp when the issue was submitted (DateTime)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    store = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    # Path/URL of the original issue photo
    issue_photo = Column(String, nullable=False)
    # Owner of the issue (who is responsible for fixing it)
    issue_owner = Column(String, nullable=False, default="门店")
    # Store sector/柜组 (nullable, only applies when issue_owner is '门店')
    # Options: "食品", "非食", "生鲜", "其他"
    store_sector = Column(String, nullable=True)
    # Path/URL of the rectification photo (nullable until fixed)
    fix_photo = Column(String, nullable=True)
    # Comments added during rectification
    fix_comments = Column(Text, nullable=True)
    # Timestamp when the rectification was submitted
    fix_date = Column(DateTime(timezone=True), nullable=True)
    # 'pending' (no fix yet) or 'completed'
    status = Column(String, nullable=False, default="pending")
