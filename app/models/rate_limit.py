from sqlalchemy import String, Integer, Column, DateTime
from app.db.base import Base


class RateLimitEntry(Base):
    __tablename__ = "rate_limit_entries"

    # Composite key: e.g. "auth:ip:127.0.0.1" or "api:user:uuid"
    key = Column(String, primary_key=True, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    count = Column(Integer, nullable=False, default=1)
