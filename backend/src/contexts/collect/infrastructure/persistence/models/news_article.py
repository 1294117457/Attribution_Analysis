"""全市场快讯 ORM 模型（Tushare news 接口）

接口: Tushare pro.news(start_date, end_date, src)
物理表名: news_article
UK: (source, url)
"""

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Index, UniqueConstraint, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class NewsArticleDB(RawBase, TimestampMixin):
    """新闻快讯（Tushare news 接口）

    一行 = 一条新闻全文
    """

    __tablename__ = "news_article"

    # id 用 bigint（新闻数据增长快）
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="文档字段 datetime")
    source: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="文档字段 src")
    channels: Mapped[str | None] = mapped_column(Text, nullable=True, comment="文档字段 channels(逗号分隔或 JSON)")

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="文档字段 content")
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # 关联股票（PostgreSQL ARRAY）
    symbols: Mapped[list | None] = mapped_column(ARRAY(String(10)), nullable=True, comment="关联股票 symbol 数组")

    # AI 情感分析（后续 NLP 模型填充）
    sentiment: Mapped[float | None] = mapped_column(String(16), nullable=True, comment="利好/利空/中性 — 后续 AI 填充")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="分类 — 后续 AI 填充")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("source", "url", name="uq_news_article_source_url"),
        Index("ix_news_article_published_at", "published_at"),
        Index("ix_news_article_source", "source"),
        Index("ix_news_article_symbols", "symbols", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<NewsArticleDB {self.published_at} {self.title[:30]}>"


__all__ = ["NewsArticleDB"]
