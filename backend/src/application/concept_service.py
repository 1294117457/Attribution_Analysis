"""概念应用服务

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §2.1
"""

from __future__ import annotations

import logging
from typing import Optional

from application.dto.concept import (
    ConceptDetailVO,
    ConceptItemVO,
    ConceptLiveVO,
    ConceptMemberVO,
    ConceptQueryRequest,
    ConceptSyncRequest,
    ConceptSyncResultVO,
    ConceptTabContentVO,
    ConceptTabSectionVO,
    CONCEPT_TYPE_LABELS,
    CONCEPT_TYPE_ORDER,
)
from application.dto.page import Page
from domain.concept.exceptions import ConceptNotFoundError
from domain.concept.repository import ConceptRepository
from domain.concept.value_objects import CONCEPT_TYPE_PRIORITY, ConceptBriefVO
from infrastructure.collectors.adata.fetcher import AdataConceptFetcher
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.collectors.registry import get_registry
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.tasks.concept_sync_operation import ConceptSyncOperation

logger = logging.getLogger(__name__)


class ConceptAppService:
    """概念应用服务

    职责：
    - 同步：触发采集器同步概念数据（默认 AKShare，支持 THS 回退）
    - 查询：列表 / 详情 / 反查（供 panel 调用）
    - 实时反查：按股票获取 adata 独家数据（带入选理由，不入 DB）
    """

    def __init__(
        self,
        repo: ConceptRepository,
        fetcher: ConceptFetcher,
        adata_fetcher: Optional[AdataConceptFetcher] = None,
    ):
        self._repo = repo
        self._fetcher = fetcher
        # adata 反查 fetcher 可选注入；未注入时按需从 registry 取
        self._adata_fetcher = adata_fetcher

    # ── 同步 ─────────────────────────────────────────

    async def sync_concepts(self, req: ConceptSyncRequest) -> ConceptSyncResultVO:
        """全量/增量同步概念数据"""
        operation = ConceptSyncOperation(repo=self._repo, fetcher=self._fetcher)
        result = await operation.sync_all()

        return ConceptSyncResultVO(
            total_concepts=result.total_concepts,
            total_members=result.total_members,
            failed_concepts=result.failed_concepts,
            elapsed_ms=result.elapsed_ms,
            synced_at=result.synced_at,
        )

    # ── 查询 ─────────────────────────────────────────

    async def query_concepts(
        self, req: ConceptQueryRequest
    ) -> Page[ConceptItemVO]:
        """分页查询概念列表"""
        concepts, total = await self._repo.list_concepts(
            q=req.q,
            source=req.source,
            is_active=req.is_active,
            page=req.page,
            page_size=req.page_size,
        )

        items = [
            ConceptItemVO(
                concept_id=c.id,
                name=c.name,
                source=c.source.value,
                concept_type=c.concept_type.value if hasattr(c.concept_type, "value") else c.concept_type,
                stock_count=c.stock_count,
                description=c.description,
                is_active=c.is_active,
                last_synced_at=c.last_synced_at,
                first_seen_at=c.first_seen_at,
            )
            for c in concepts
        ]

        return Page[ConceptItemVO].from_list(
            items,
            total,
            req.page,
            req.page_size,
        )

    async def get_concept_detail(
        self, name: str, source: str = "em"
    ) -> ConceptDetailVO:
        """概念详情（含成分股）"""
        concept = await self._repo.get_concept_by_name(name=name, source=source)
        if not concept:
            raise ConceptNotFoundError(name=name)

        # 获取成分股（实时拉取）
        stock_bos = self._fetcher.fetch_concept_stocks(name)
        members = [
            ConceptMemberVO(
                symbol=s.symbol,
                name=s.name,
                rank=s.rank,
                latest_price=s.latest_price,
            )
            for s in stock_bos
        ]

        return ConceptDetailVO(
            concept_id=concept.id,
            name=concept.name,
            source=concept.source.value,
            concept_type=concept.concept_type.value if hasattr(concept.concept_type, "value") else concept.concept_type,
            stock_count=concept.stock_count,
            description=concept.description,
            is_active=concept.is_active,
            last_synced_at=concept.last_synced_at,
            first_seen_at=concept.first_seen_at,
            members=members,
        )

    # ── 反向查询（供 panel 复用）──────────────────────

    async def list_for_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        return await self._repo.list_concepts_by_symbol(symbol)

    async def list_for_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询（避免 N+1）"""
        return await self._repo.list_concepts_by_symbols(symbols)

    async def list_for_symbols_with_snapshots(
        self, symbols: list[str]
    ) -> dict[str, dict[str, dict]]:
        """批量反查 + 批量取快照（避免 N+1，09concept 新增）

        Returns: {symbol: {concept_name: snapshot_dict, ...}, ...}
        用于主概念 Tag 涨跌染色：
        - 先 list_concepts_by_symbols(symbols) 拿到 symbol → concepts
        - 收集所有 concept_name，单次 SQL 取最新快照
        - 返回嵌套 dict
        """
        briefs_map = await self._repo.list_concepts_by_symbols(symbols)

        all_names: set[str] = set()
        for briefs in briefs_map.values():
            for b in briefs:
                all_names.add(b.name)

        if not all_names:
            return {s: {} for s in symbols}

        snaps = await self._repo.list_snapshots_for_names(list(all_names))

        out: dict[str, dict[str, dict]] = {}
        for sym in symbols:
            briefs = briefs_map.get(sym, [])
            out[sym] = {b.name: snaps.get(b.name, {}) for b in briefs}
        return out

    # ── 实时反查（adata 独家能力）─────────────────────

    def _get_adata_fetcher(self) -> Optional[AdataConceptFetcher]:
        """获取 adata fetcher（懒加载：首次调用时从 registry 取）"""
        if self._adata_fetcher is not None:
            return self._adata_fetcher
        try:
            registry = get_registry()
            # 工厂可能返回 AdataConceptFetcher，也可能返回单例 AkShare
            fetcher = registry.create(ConceptFetcher)
            if isinstance(fetcher, AdataConceptFetcher):
                self._adata_fetcher = fetcher
                return fetcher
        except Exception as e:
            logger.warning("获取 AdataConceptFetcher 失败: %s", e)
        return None

    def fetch_concepts_by_stock(self, symbol: str) -> list[ConceptLiveVO]:
        """按股票代码实时反查所属概念（adata 独家，带入选理由）

        数据源优先级：
        1. AdataConceptFetcher（带入选理由，0.5s/股票）
        2. 注入的普通 fetcher（akshare 通常不支持，返回空）

        返回 ConceptLiveVO 列表（不入 DB，实时拉取）：
        - concept_code (如 "BK0683")
        - name (如 "央国企改革")
        - source = "adata"
        - reason (入选理由，如 "公司有深圳国资背景。")

        应用场景：详情抽屉「概念」Tab 的"实时补充"按钮 / 搜索框联想。
        """
        adata = self._get_adata_fetcher()
        if adata is None:
            logger.debug(
                "fetch_concepts_by_stock(%s): adata 不可用，返回空",
                symbol,
            )
            return []

        bos = adata.fetch_concepts_by_stock(symbol)
        return [
            ConceptLiveVO(
                concept_code=bo.code,
                name=bo.name,
                source=bo.source.value,
                reason=bo.reason,
            )
            for bo in bos
        ]

    # ── 详情抽屉「概念」Tab 专用 ──────────────────────

    async def get_tab_content_for_symbol(
        self,
        symbol: str,
        stock_name: Optional[str] = None,
    ) -> ConceptTabContentVO:
        """详情抽屉「概念」Tab 的完整渲染模型

        步骤：
        ① 拉取该股票所属的所有活跃概念（含 concept_type / description）
        ② 批量取这些概念的最新行情快照（09concept 新增）
        ③ 按 concept_type 分组，按预定顺序排序
        ④ 组装为 ConceptTabContentVO，前端 ConceptTab.vue 直接消费

        每个概念携带 snapshot 字段（可能为 None 表示暂无快照数据）
        """
        grouped_vos = await self._repo.list_concepts_by_symbol_grouped(symbol)

        # 09concept：批量取行情快照（避免 N+1）
        all_names = [v.name for v in grouped_vos]
        snap_map = (
            await self._repo.list_snapshots_for_names(all_names)
            if all_names else {}
        )

        bucket: dict[str, list] = {t: [] for t in CONCEPT_TYPE_ORDER}
        for vo in grouped_vos:
            snap = snap_map.get(vo.name)
            bucket.setdefault(vo.concept_type, []).append({
                "concept_id": vo.concept_id,
                "name": vo.name,
                "source": vo.source,
                "concept_type": vo.concept_type,
                "description": vo.description,
                "snapshot": snap,  # 09concept 新增
            })

        sections = [
            ConceptTabSectionVO(
                type=t,
                type_label=CONCEPT_TYPE_LABELS.get(t, t),
                concepts=sorted(bucket[t], key=lambda x: x["name"]),
            )
            for t in CONCEPT_TYPE_ORDER
            if bucket[t]
        ]

        return ConceptTabContentVO(
            symbol=symbol,
            stock_name=stock_name or "",
            sections=sections,
            total_count=sum(len(s.concepts) for s in sections),
        )

    # ── 08concept 新增：实时合并版 Tab 内容 ──────────────────────

    async def get_tab_content_with_live(
        self,
        symbol: str,
        stock_name: Optional[str] = None,
    ) -> ConceptTabContentVO:
        """详情抽屉「概念」Tab 合并 DB + adata 实时数据

        实现策略：
        - DB 异步拉取（list_concepts_by_symbol_grouped）
        - adata 实时拉取（fetch_concepts_by_stock，同步方法）
        - 按 (name, source) 去重合并，dict 行携带 is_realtime / reason 字段
        - 排序：实时优先（reason 含金量高）→ type 优先级 → name

        失败容忍：
        - adata 网络故障 → 仅返回 DB 数据
        - DB 为空 + adata 有数据 → 仅实时数据
        """
        # 1. DB 异步拉取
        grouped_vos = await self._repo.list_concepts_by_symbol_grouped(symbol)

        # 2. adata 实时拉取（失败时返回空 list，不抛错）
        live_vos: list[ConceptLiveVO] = []
        try:
            live_vos = self.fetch_concepts_by_stock(symbol)
        except Exception as e:
            logger.warning("实时反查 %s 失败，降级为仅 DB: %s", symbol, e)

        # 09concept：批量取 DB 概念的快照（用于合并前填充 snapshot 字段）
        all_db_names = [v.name for v in grouped_vos]
        snap_map = (
            await self._repo.list_snapshots_for_names(all_db_names)
            if all_db_names else {}
        )

        # 3. 合并去重（用 (name, source) 做 key）
        db_index: dict[tuple[str, str], dict] = {
            (v.name, v.source): {
                "concept_id": v.concept_id,
                "name": v.name,
                "source": v.source,
                "concept_type": v.concept_type,
                "description": v.description,
                "concept_code": None,
                "is_realtime": False,
                "reason": None,
                "snapshot": snap_map.get(v.name),  # 09concept
            }
            for v in grouped_vos
        }
        live_index: dict[tuple[str, str], ConceptLiveVO] = {
            (v.name, v.source): v for v in live_vos
        }

        all_keys = set(db_index.keys()) | set(live_index.keys())
        merged_rows: list[dict] = []
        for key in all_keys:
            db_row = db_index.get(key)
            live_row = live_index.get(key)
            if db_row and live_row:
                # 共有：实时数据优先（更新 reason），保留 DB 的 concept_id 和 description
                merged_rows.append({
                    **db_row,
                    "concept_code": live_row.concept_code,
                    "is_realtime": True,
                    "reason": live_row.reason,
                })
            elif db_row:
                merged_rows.append(db_row)
            else:
                # live-only：无 concept_id
                merged_rows.append({
                    "concept_id": None,
                    "concept_code": live_row.concept_code,
                    "name": live_row.name,
                    "source": live_row.source,
                    "concept_type": "other",  # adata 不提供 type
                    "description": None,
                    "is_realtime": True,
                    "reason": live_row.reason,
                    "snapshot": snap_map.get(live_row.name),  # 09concept
                })

        # 4. 排序：实时优先 → type 优先级 → name
        merged_rows.sort(
            key=lambda r: (
                0 if r["is_realtime"] else 1,
                CONCEPT_TYPE_PRIORITY.get(r["concept_type"], 99),
                r["name"],
            ),
        )

        # 5. 按 type 分组组装 ConceptTabContentVO
        bucket: dict[str, list[dict]] = {t: [] for t in CONCEPT_TYPE_ORDER}
        for row in merged_rows:
            bucket.setdefault(row["concept_type"], []).append(row)

        from datetime import datetime, timezone

        sections = [
            ConceptTabSectionVO(
                type=t,
                type_label=CONCEPT_TYPE_LABELS.get(t, t),
                concepts=sorted(bucket[t], key=lambda r: r["name"]),
            )
            for t in CONCEPT_TYPE_ORDER
            if bucket[t]
        ]

        return ConceptTabContentVO(
            symbol=symbol,
            stock_name=stock_name or "",
            sections=sections,
            total_count=len(merged_rows),
            is_merged=True,
            last_merged_at=datetime.now(timezone.utc),
        )


# ── 依赖注入工厂 ──────────────────────────────────────

async def get_concept_app_service(
    session,  # AsyncSession
) -> ConceptAppService:
    """构造 ConceptAppService 实例

    从 FetcherRegistry 获取已注册的 fetcher。
    """
    from infrastructure.collectors.registry import get_registry
    from infrastructure.collectors.protocols import ConceptFetcher

    repo = ConceptRepoImpl(session)
    registry = get_registry()
    fetcher = registry.get(ConceptFetcher)
    return ConceptAppService(repo=repo, fetcher=fetcher)
