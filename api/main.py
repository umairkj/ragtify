# The main FastAPI app entry point
# All logic is in app/ submodules

from sqlalchemy.ext.declarative import declarative_base
from app.db.base import Base

# Export Base for Alembic migrations
__all__ = ["Base"] 