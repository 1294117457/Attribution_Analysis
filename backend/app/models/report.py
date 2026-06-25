"""分析报告模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Report(Base):
    """分析报告表 - 存储归因分析结果"""

    __tablename__ = "reports"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联股票
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="股票代码")
    name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="股票名称")

    # 分析参数
    start_date: Mapped[str] = mapped_column(String(10), nullable=False, comment="开始日期")
    end_date: Mapped[str] = mapped_column(String(10), nullable=False, comment="结束日期")
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="分析类型")

    # 分析结果
    report_content: Mapped[str] = mapped_column(Text, nullable=False, comment="报告内容(Markdown)")
    anomalies: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="检测到的异常(JSON)")
    attribution: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="归因分析结果(JSON)")

    # 置信度
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True, comment="置信度(0-1)")

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_code_created", "code", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, code={self.code}, type={self.analysis_type})>"
