from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import LONGTEXT, JSON, DECIMAL
from datetime import datetime, timezone
from enum import Enum as PyEnum
from app.db.base import Base
from app.schemas.task import TaskStatus
from decimal import Decimal

if TYPE_CHECKING:
    from .user import User


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.FAILED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    result: Mapped[str] = mapped_column(LONGTEXT, nullable=True)
    debug_info: Mapped[str] = mapped_column(LONGTEXT, nullable=True)
    cost: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), nullable=True)
    route_name: Mapped[str] = mapped_column(String(100), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="tasks")
