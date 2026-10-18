"""concept context — 业务 DI 工厂

仅负责：组装 ConceptService / ConceptBoardService。

依赖 collect 的 fetcher（取 concept_minute / stock_concepts）—— 跨 context
依赖通过 fetcher 内部 lazy init 的 SDK 单例完成，不需要 ServiceRegistry。
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db, get_raw_db


def get_concept_service(
    raw_session: AsyncSession = Depends(get_raw_db),
    attr_session: AsyncSession = Depends(get_db),
):
    """ConceptService 工厂（双 session：业务库 + 采集库）"""
    from contexts.collect.application.service.fundamental.stock_concepts_service import (
        StockConceptsService,
    )
    from contexts.collect.infrastructure.fetcher.fundamental.ConceptMinuteAdataFetcher import (
        ConceptMinuteAdataFetcher,
    )
    from contexts.concept.application.service.concept_realtime import ConceptRealtimeReader
    from contexts.concept.application.service.concept_service import ConceptService
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import (
        ConceptRepoImpl,
    )

    repo = ConceptRepoImpl(raw_session, attr_session)
    return ConceptService(
        repo=repo,
        realtime=ConceptRealtimeReader(
            repo,
            minute_fetcher=ConceptMinuteAdataFetcher(),
        ),
        stock_concepts_svc=StockConceptsService(),
    )


def get_concept_board_service(
    raw_session: AsyncSession = Depends(get_raw_db),
    attr_session: AsyncSession = Depends(get_db),
):
    """ConceptBoardService 工厂（双 session）"""
    from contexts.concept.application.service.concept_board_service import ConceptBoardService
    from contexts.concept.application.service.concept_realtime import ConceptRealtimeReader
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import (
        ConceptRepoImpl,
    )

    repo = ConceptRepoImpl(raw_session, attr_session)
    return ConceptBoardService(repo=repo, realtime=ConceptRealtimeReader(repo))


__all__ = ["get_concept_service", "get_concept_board_service"]
