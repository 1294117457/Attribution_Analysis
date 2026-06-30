"""FastAPI 依赖"""

from app.database.connection import get_db_session

__all__ = ["get_db_session"]
