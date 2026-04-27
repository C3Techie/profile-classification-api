from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so SQLAlchemy registers them before create_all is called.
# This must come AFTER Base is defined to avoid circular imports.
from app.models import profile, user, token, rate_limit  # noqa: F401, E402
