"""concept context — DI 工厂聚合"""
from contexts.concept.infrastructure.di.concept_service import (
    get_concept_board_service,
    get_concept_service,
)

__all__ = ["get_concept_service", "get_concept_board_service"]
