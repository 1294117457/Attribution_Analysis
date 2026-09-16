"""base_name_change — 仓储接口"""

from abc import ABC, abstractmethod

from domain.base_name_change.entity import BaseNameChange


class BaseNameChangeRepository(ABC):
    @abstractmethod
    async def save(self, entity: BaseNameChange) -> BaseNameChange: ...
    @abstractmethod
    async def save_batch(self, entities: list[BaseNameChange]) -> int: ...
    @abstractmethod
    async def find_by_symbol(self, symbol: str) -> list[BaseNameChange]: ...
