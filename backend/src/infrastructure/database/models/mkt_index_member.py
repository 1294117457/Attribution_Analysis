"""板块成分 ORM 模型"""

from datetime import date
from sqlalchemy import String, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class MktIndexMemberDB(Base, TimestampMixin):
    """板块成分股

    物理表名: mkt_index_members
    UK: (sector_type, sector_code, symbol, effective_date)
    """

    __tablename__ = "mkt_index_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sector_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="板块类型: industry/concept/area")
    sector_code: Mapped[str] = mapped_column(String(32), nullable=False, comment="板块代码")
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="纳入日期")
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="剔除日期")
    is_new: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="Y/N")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "sector_type", "sector_code", "symbol", "effective_date",
            name="uq_mkt_index_members_uk",
        ),
        Index("ix_mkt_index_members_sector", "sector_type", "sector_code"),
    )

    def __repr__(self) -> str:
        return f"<MktIndexMemberDB {self.sector_code} {self.symbol}>"
