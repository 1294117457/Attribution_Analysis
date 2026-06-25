"""Initial migration - create tables

Revision ID: 001
Revises:
Create Date: 2026-06-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 klines 表
    op.create_table(
        "klines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=False, comment="股票代码"),
        sa.Column("name", sa.String(50), nullable=False, comment="股票名称"),
        sa.Column("date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("open", sa.Float(), nullable=False, comment="开盘价"),
        sa.Column("high", sa.Float(), nullable=False, comment="最高价"),
        sa.Column("low", sa.Float(), nullable=False, comment="最低价"),
        sa.Column("close", sa.Float(), nullable=False, comment="收盘价"),
        sa.Column("volume", sa.Float(), nullable=False, comment="成交量(手)"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额(元)"),
        sa.Column("change_pct", sa.Float(), nullable=True, comment="涨跌幅(%)"),
        sa.Column("turnover_rate", sa.Float(), nullable=True, comment="换手率(%)"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_code_date", "klines", ["code", "date"], unique=True)

    # 创建 news 表
    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=True, comment="股票代码"),
        sa.Column("title", sa.String(500), nullable=False, comment="新闻标题"),
        sa.Column("content", sa.Text(), nullable=True, comment="新闻内容摘要"),
        sa.Column("url", sa.String(1000), nullable=True, comment="原文链接"),
        sa.Column("source", sa.String(100), nullable=True, comment="新闻来源"),
        sa.Column("publish_time", sa.DateTime(), nullable=True, comment="发布时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_code_publish", "news", ["code", "publish_time"])

    # 创建 reports 表
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=False, comment="股票代码"),
        sa.Column("name", sa.String(50), nullable=True, comment="股票名称"),
        sa.Column("start_date", sa.String(10), nullable=False, comment="开始日期"),
        sa.Column("end_date", sa.String(10), nullable=False, comment="结束日期"),
        sa.Column("analysis_type", sa.String(50), nullable=False, comment="分析类型"),
        sa.Column("report_content", sa.Text(), nullable=False, comment="报告内容"),
        sa.Column("anomalies", sa.JSON(), nullable=True, comment="异常列表"),
        sa.Column("attribution", sa.JSON(), nullable=True, comment="归因结果"),
        sa.Column("confidence", sa.Float(), nullable=True, comment="置信度"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_code_created", "reports", ["code", "created_at"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("news")
    op.drop_table("klines")
