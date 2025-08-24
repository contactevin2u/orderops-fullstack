from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    CASHIER = "CASHIER"
    DRIVER = "DRIVER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[Role] = mapped_column(Enum(Role))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debugging only
        return f"<User username={self.username!r} role={self.role}>"

