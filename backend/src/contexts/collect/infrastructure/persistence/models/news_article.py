"""新闻快讯 ORM 模型"""

from datetime import datetime
from sqlalchemy import String, Float, Date, Time, Index, UniqueConstraint, Integer, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TIMESTAMP

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class NewsArticleDB(RawBase, TimestampMixin):
    """新闻快讯

    物理表名: news_article
    UK: (source, url)
    数据来源: Tushare news / Adata
    """

    __tablename__ = "news_article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 来源
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 新浪/东方财富/财联社
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # 关联股票（PostgreSQL ARRAY）
    symbols: Mapped[list | None] = mapped_column(ARRAY(String(10)), nullable=True)

    # AI 情感分析（后续 NLP 模型填充）
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1 ~ 1
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 利好/利空/中性/行业

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("source", "url", name="uq_news_article_source_url"),
        Index("ix_news_article_published_at", "published_at"),
        Index("ix_news_article_symbols", "symbols", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<NewsArticleDB {self.published_at} {self.title[:30]}>"


__all__ = ["NewsArticleDB"]
