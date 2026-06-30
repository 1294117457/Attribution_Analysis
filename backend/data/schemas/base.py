"""数据管道基类"""

from pydantic import BaseModel


class BaseData(BaseModel):
    """所有采集数据的基类"""
    pass
