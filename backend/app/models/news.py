"""新闻数据模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class News(Base):
    """新闻表 - 存储股票相关新闻"""

    __tablename__ = "news"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联股票
    code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True, comment="股票代码")

    # 新闻信息
    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="新闻标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="新闻内容摘要")
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="原文链接")

    # 来源和时间
    source: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="新闻来源")
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="发布时间")

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_code_publish", "code", "publish_time"),
    )

    def __repr__(self) -> str:
        return f"<News(id={self.id}, code={self.code}, title={self.title[:30]}...)>"
