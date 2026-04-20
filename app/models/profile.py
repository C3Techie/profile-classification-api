from sqlalchemy import String, Float, Integer, Column, DateTime
from app.db.base import Base
from datetime import datetime, timezone

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True) # UUID v7
    name = Column(String, unique=True, index=True, nullable=False)
    gender = Column(String, nullable=False, index=True)
    gender_probability = Column(Float, nullable=False)
    age = Column(Integer, nullable=False, index=True)
    age_group = Column(String, nullable=False, index=True)
    country_id = Column(String(2), nullable=False, index=True)
    country_name = Column(String, nullable=False)
    country_probability = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
