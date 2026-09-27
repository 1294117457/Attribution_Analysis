"""mkt_index_member — 仓储接口"""

from abc import ABC, abstractmethod

from domain.entitys.mkt_index_member.entity import MktIndexMember


class MktIndexMemberRepository(ABC):
    """指数成分股仓储（主键 sector_type + sector_code + symbol）"""

    @abstractmethod
    async def save(self, entity: MktIndexMember) -> MktIndexMember: ...

    @abstractmethod
    async def save_batch(self, entities: list[MktIndexMember]) -> int: ...

    @abstractmethod
    async def find_by_sector(
        self,
        sector_type: str,
        sector_code: str,
    ) -> list[MktIndexMember]: ...
