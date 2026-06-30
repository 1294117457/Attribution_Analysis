"""FastAPI 依赖注入出口"""

from infra.database.connection import get_db_session

__all__ = ["get_db_session"]
