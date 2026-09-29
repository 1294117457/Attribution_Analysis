"""P0 单测：3 个数据源 + Pipeline 单步 + Pipeline 多步 + 模板渲染 + UnitResolver"""

import pytest

from application.port.data_source_api import (
    CallResult,
    ConceptAPI,
    DailyBasicAPI,
    DataSourceAPI,
    FinReportAPI,
    KlineAPI,
    MinuteKlineAPI,
    StockBasicAPI,
)
from infrastructure.adapter.data_source import AdataAPI, PytdxAPI, TushareAPI
from infrastructure.adapter.data_source.registry import (
    DataSourceRegistry,
    get_data_source_registry,
)
from infrastructure.adapter.pipeline import (
    APIStep,
    Pipeline,
    PipelineRegistry,
    PipelineRunner,
    RateLimitConfig,
    ScheduleSpec,
    UnitSpec,
)
from infrastructure.adapter.pipeline.template import render


# ═══════════════════════════════════════════════════════════════════════
# 1. CallResult 基础
# ═══════════════════════════════════════════════════════════════════════


def test_call_result_success():
    r = CallResult.success(data=[1, 2, 3], source="test", elapsed_ms=100)
    assert r.ok is True
    assert r.data == [1, 2, 3]
    assert r.source == "test"
    assert r.error is None


def test_call_result_failure():
    r = CallResult.failure("oops", source="test", error_type="rate_limited")
    assert r.ok is False
    assert r.error == "oops"
    assert r.error_type == "rate_limited"


# ═══════════════════════════════════════════════════════════════════════
# 2. 模板渲染
# ═══════════════════════════════════════════════════════════════════════


def test_render_simple_var():
    assert render("{{symbol}}", {"symbol": "600519"}) == "600519"


def test_render_attr_access():
    assert render("{{params.days}}", {"params": {"days": 7}}) == "7"


def test_render_dict():
    tmpl = {"symbol": "{{s}}", "days": "{{d}}"}
    assert render(tmpl, {"s": "600519", "d": 30}) == {"symbol": "600519", "days": "30"}


def test_render_list():
    assert render(["{{a}}", "{{b}}"], {"a": 1, "b": 2}) == ["1", "2"]


def test_render_missing_var_returns_empty():
    """找不到变量时返回空串，不抛错"""
    assert render("{{unknown}}", {}) == ""


def test_render_nested():
    tmpl = {"config": {"name": "{{n}}", "count": "{{c}}"}}
    assert render(tmpl, {"n": "test", "c": 5}) == {"config": {"name": "test", "count": "5"}}


def test_render_no_vars_passthrough():
    """无变量的字符串原样返回"""
    assert render("hello", {}) == "hello"


# ═══════════════════════════════════════════════════════════════════════
# 3. Protocol 自检
# ═══════════════════════════════════════════════════════════════════════


def test_tushare_api_implements_protocols():
    """TushareAPI 必须实现 4 个细粒度协议"""
    api = TushareAPI()
    assert isinstance(api, DataSourceAPI)
    assert isinstance(api, KlineAPI)
    assert isinstance(api, DailyBasicAPI)
    assert isinstance(api, StockBasicAPI)
    assert isinstance(api, FinReportAPI)
    assert api.source_name == "Tushare"
    assert "fetch_kline" in api.available_methods
    assert "fetch_income" in api.available_methods


def test_pytdx_api_implements_protocols():
    api = PytdxAPI()
    assert isinstance(api, DataSourceAPI)
    assert isinstance(api, MinuteKlineAPI)
    assert api.source_name == "Pytdx"
    assert "fetch_minute_klines" in api.available_methods


def test_adata_api_implements_protocols():
    api = AdataAPI()
    assert isinstance(api, DataSourceAPI)
    assert isinstance(api, ConceptAPI)
    assert api.source_name == "Adata-THS"
    assert "fetch_concept_list" in api.available_methods


# ═══════════════════════════════════════════════════════════════════════
# 4. TushareAPI 调用（mock 内部 fetcher）
# ═══════════════════════════════════════════════════════════════════════


class FakeTushareFetcher:
    """假 TushareFetcher，只模拟 fetch / fetch_daily_basic / fetch_stock_basic / fetch_income"""

    def __init__(self):
        self.calls = []

    def fetch(self, params):
        self.calls.append(("fetch", params.symbol, params.days))
        return [f"kline:{params.symbol}:{params.days}"]

    def fetch_daily_basic(self, trade_date):
        self.calls.append(("fetch_daily_basic", trade_date))
        return [f"daily_basic:{trade_date}"]

    def fetch_stock_basic(self, params):
        self.calls.append(("fetch_stock_basic", params.list_status))
        return [f"stock_basic:{params.list_status}"]

    def fetch_income(self, ts_code, start_date=None, end_date=None):
        self.calls.append(("fetch_income", ts_code, start_date))
        return [f"income:{ts_code}:{start_date}"]


@pytest.mark.asyncio
async def test_tushare_api_fetch_kline():
    fake = FakeTushareFetcher()
    api = TushareAPI(fetcher=fake)

    result = await api.fetch_kline(symbol="600519", days=30)

    assert result.ok is True
    assert result.data == ["kline:600519:30"]
    assert result.source == "Tushare"
    assert fake.calls == [("fetch", "600519", 30)]


@pytest.mark.asyncio
async def test_tushare_api_fetch_daily_basic():
    fake = FakeTushareFetcher()
    api = TushareAPI(fetcher=fake)

    result = await api.fetch_daily_basic(trade_date="20240901")

    assert result.ok is True
    assert result.data == ["daily_basic:20240901"]
    assert fake.calls == [("fetch_daily_basic", "20240901")]


@pytest.mark.asyncio
async def test_tushare_api_fetch_stock_basic():
    fake = FakeTushareFetcher()
    api = TushareAPI(fetcher=fake)

    result = await api.fetch_stock_basic(list_status="L")

    assert result.ok is True
    assert result.data == ["stock_basic:L"]
    assert fake.calls == [("fetch_stock_basic", "L")]


@pytest.mark.asyncio
async def test_tushare_api_fetch_income():
    fake = FakeTushareFetcher()
    api = TushareAPI(fetcher=fake)

    result = await api.fetch_income(ts_code="600519.SH", start_date="20240101")

    assert result.ok is True
    assert result.data == ["income:600519.SH:20240101"]


@pytest.mark.asyncio
async def test_tushare_api_fetch_kline_failure():
    class BrokenFetcher:
        def fetch(self, params):
            raise RuntimeError("tushare token invalid")

    api = TushareAPI(fetcher=BrokenFetcher())
    result = await api.fetch_kline(symbol="600519", days=30)

    assert result.ok is False
    assert "tushare token invalid" in result.error


# ═══════════════════════════════════════════════════════════════════════
# 5. DataSourceRegistry
# ═══════════════════════════════════════════════════════════════════════


def test_registry_register_and_get():
    reg = DataSourceRegistry()
    fake = FakeTushareFetcher()
    api = TushareAPI(fetcher=fake)

    reg.register_instance("Tushare", api)

    assert "Tushare" in reg.list_sources()
    assert reg.get("Tushare") is api
    assert reg.has("Tushare")
    assert "fetch_kline" in reg.list_methods("Tushare")
    assert reg.validate_method("Tushare", "fetch_kline") is True
    assert reg.validate_method("Tushare", "unknown_method") is False


def test_registry_get_unregistered_raises():
    reg = DataSourceRegistry()
    with pytest.raises(KeyError, match="UnknownSource"):
        reg.get("UnknownSource")


# ═══════════════════════════════════════════════════════════════════════
# 6. Pipeline 构造 + 校验
# ═══════════════════════════════════════════════════════════════════════


def test_pipeline_construct_basic():
    p = Pipeline(
        pipeline_id="test",
        name="测试",
        steps=(APIStep(name="s1", source="Tushare", method="fetch_kline", args_template={"symbol": "{{symbol}}"}),),
    )
    assert p.pipeline_id == "test"
    assert len(p.steps) == 1


def test_pipeline_empty_steps_raises():
    with pytest.raises(ValueError, match="至少有 1 个 step"):
        Pipeline(pipeline_id="test", name="测试", steps=())


def test_pipeline_duplicate_step_names_raises():
    with pytest.raises(ValueError, match="step 名重复"):
        Pipeline(
            pipeline_id="test",
            name="测试",
            steps=(
                APIStep(name="s1", source="Tushare", method="fetch_kline"),
                APIStep(name="s1", source="Tushare", method="fetch_daily_basic"),
            ),
        )


def test_pipeline_invalid_depends_on_raises():
    with pytest.raises(ValueError, match="不存在的上游"):
        Pipeline(
            pipeline_id="test",
            name="测试",
            steps=(
                APIStep(name="s1", source="Tushare", method="fetch_kline"),
                APIStep(name="s2", source="Tushare", method="fetch_daily_basic", depends_on=("nonexistent",)),
            ),
        )


# ═══════════════════════════════════════════════════════════════════════
# 7. PipelineRegistry + 校验
# ═══════════════════════════════════════════════════════════════════════


def test_pipeline_registry_validate():
    reg = DataSourceRegistry()
    fake = FakeTushareFetcher()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake))

    pr = PipelineRegistry(data_source_registry=reg)
    pr.register(Pipeline(
        pipeline_id="valid",
        name="Valid",
        steps=(APIStep(name="s1", source="Tushare", method="fetch_kline"),),
    ))
    pr.register(Pipeline(
        pipeline_id="invalid_method",
        name="Invalid Method",
        steps=(APIStep(name="s1", source="Tushare", method="unknown_method"),),
    ))
    pr.register(Pipeline(
        pipeline_id="invalid_source",
        name="Invalid Source",
        steps=(APIStep(name="s1", source="UnknownSource", method="fetch_kline"),),
    ))

    errors = pr.validate()
    assert len(errors) == 2
    assert any("invalid_method" in e and "unknown_method" in e for e in errors)
    assert any("invalid_source" in e and "UnknownSource" in e for e in errors)


def test_pipeline_registry_filter_by_tag():
    reg = DataSourceRegistry()
    pr = PipelineRegistry(data_source_registry=reg)
    p1 = Pipeline(pipeline_id="a", name="A", steps=(APIStep(name="s", source="Tushare", method="fetch_kline"),), tags=("盘后", "Tushare"))
    p2 = Pipeline(pipeline_id="b", name="B", steps=(APIStep(name="s", source="Adata-THS", method="fetch_concept_list"),), tags=("盘后",))
    p3 = Pipeline(pipeline_id="c", name="C", steps=(APIStep(name="s", source="Pytdx", method="fetch_minute_klines"),), tags=("盘中",))
    pr.register_all([p1, p2, p3])

    assert {p.pipeline_id for p in pr.list_by_tag("盘后")} == {"a", "b"}
    assert {p.pipeline_id for p in pr.list_by_tag("Tushare")} == {"a"}
    assert {p.pipeline_id for p in pr.list_by_source("Tushare")} == {"a"}


# ═══════════════════════════════════════════════════════════════════════
# 8. PipelineRunner 单步
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_runner_one_shot_single_step():
    fake = FakeTushareFetcher()
    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake))

    pipeline = Pipeline(
        pipeline_id="one_shot_kline",
        name="One-shot kline",
        unit=UnitSpec(style="one_shot"),
        steps=(APIStep(
            name="fetch_all",
            source="Tushare",
            method="fetch_kline",
            args_template={"symbol": "ALL", "days": 30},
        ),),
    )

    runner = PipelineRunner(reg, pipeline)
    summary = await runner.run()

    assert summary.total == 1
    assert summary.success == 1
    assert summary.fail == 0
    assert fake.calls == [("fetch", "ALL", 30)]


@pytest.mark.asyncio
async def test_pipeline_runner_per_unit_multi_unit():
    """per_unit 风格：从 unit_source 拉多个 unit，每个 unit 跑一次 step"""
    fake = FakeTushareFetcher()
    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake))

    pipeline = Pipeline(
        pipeline_id="daily_kline",
        name="Daily Kline",
        unit=UnitSpec(
            style="per_unit",
            unit_source="stock_infos",
            unit_template={"label": "{{symbol}}", "symbol": "{{symbol}}"},
        ),
        steps=(APIStep(
            name="fetch_kline",
            source="Tushare",
            method="fetch_kline",
            args_template={"symbol": "{{symbol}}", "days": 30},
        ),),
    )

    runner = PipelineRunner(reg, pipeline)
    summary = await runner.run(params={"stock_symbols": ["600519", "000001"]})

    assert summary.total == 2
    assert summary.success == 2
    assert fake.calls == [("fetch", "600519", 30), ("fetch", "000001", 30)]


@pytest.mark.asyncio
async def test_pipeline_runner_step_failure_marks_unit_fail():
    class BrokenTushareFetcher:
        def fetch(self, params):
            raise RuntimeError("simulated failure")

    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=BrokenTushareFetcher()))

    pipeline = Pipeline(
        pipeline_id="fail_test",
        name="Fail Test",
        unit=UnitSpec(
            style="per_unit",
            unit_source="stock_infos",
            unit_template={"label": "{{symbol}}", "symbol": "{{symbol}}"},
        ),
        steps=(APIStep(
            name="fetch_kline",
            source="Tushare",
            method="fetch_kline",
            args_template={"symbol": "{{symbol}}", "days": 7},
        ),),
    )

    runner = PipelineRunner(reg, pipeline)
    summary = await runner.run(params={"stock_symbols": ["600519"]})

    assert summary.total == 1
    assert summary.success == 0
    assert summary.fail == 1


# ═══════════════════════════════════════════════════════════════════════
# 9. PipelineRunner 多步工作流
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_runner_multi_step_workflow():
    """3 步工作流：fetch_kline + fetch_daily_basic + fetch_stock_basic"""
    fake = FakeTushareFetcher()
    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake))

    pipeline = Pipeline(
        pipeline_id="after_market_sync",
        name="After Market Sync",
        unit=UnitSpec(style="one_shot"),
        steps=(
            APIStep(
                name="fetch_kline",
                source="Tushare",
                method="fetch_kline",
                args_template={"symbol": "ALL", "days": 1},
            ),
            APIStep(
                name="fetch_daily_basic",
                source="Tushare",
                method="fetch_daily_basic",
                args_template={"trade_date": "{{date}}"},
            ),
            APIStep(
                name="fetch_stock_basic",
                source="Tushare",
                method="fetch_stock_basic",
                args_template={"list_status": "L"},
            ),
        ),
    )

    runner = PipelineRunner(reg, pipeline)
    summary = await runner.run(params={"date": "20240901"})

    assert summary.total == 1
    assert summary.success == 1
    assert summary.fail == 0
    assert fake.calls == [
        ("fetch", "ALL", 1),
        ("fetch_daily_basic", "20240901"),
        ("fetch_stock_basic", "L"),
    ]


@pytest.mark.asyncio
async def test_pipeline_runner_multi_step_second_step_fails():
    """多步工作流：第 2 步失败 → 整个 unit 失败，第 3 步不执行"""
    class PartialFailFetcher:
        def __init__(self):
            self.calls = []

        def fetch(self, params):
            self.calls.append("fetch")
            return ["ok"]

        def fetch_daily_basic(self, trade_date):
            self.calls.append("fetch_daily_basic")
            raise RuntimeError("daily_basic failed")

        def fetch_stock_basic(self, params):
            self.calls.append("fetch_stock_basic")
            return ["should not be called"]

    fake = PartialFailFetcher()
    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake))

    pipeline = Pipeline(
        pipeline_id="partial_fail",
        name="Partial Fail",
        unit=UnitSpec(style="one_shot"),
        steps=(
            APIStep(name="s1", source="Tushare", method="fetch_kline", args_template={"symbol": "ALL", "days": 1}),
            APIStep(name="s2", source="Tushare", method="fetch_daily_basic", args_template={"trade_date": "20240901"}),
            APIStep(name="s3", source="Tushare", method="fetch_stock_basic", args_template={"list_status": "L"}),
        ),
    )

    runner = PipelineRunner(reg, pipeline)
    summary = await runner.run()

    assert summary.success == 0
    assert summary.fail == 1
    # 第 3 步不应被调用
    assert "fetch_stock_basic" not in fake.calls


# ═══════════════════════════════════════════════════════════════════════
# 10. 跨数据源工作流（Tushare + Adata）
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_runner_cross_source_workflow():
    """多步工作流：跨 Tushare + Adata"""
    class FakeAdata:
        def __init__(self):
            self.calls = []

        def fetch_concept_list(self):
            self.calls.append("concept_list")
            return ["c1", "c2"]

    fake_tushare = FakeTushareFetcher()
    fake_adata = FakeAdata()

    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake_tushare))
    reg.register_instance("Adata-THS", AdataAPI(fetcher=fake_adata))

    pipeline = Pipeline(
        pipeline_id="cross",
        name="Cross Source",
        unit=UnitSpec(style="one_shot"),
        steps=(
            APIStep(name="fetch_kline", source="Tushare", method="fetch_kline", args_template={"symbol": "ALL", "days": 1}),
            APIStep(name="fetch_concepts", source="Adata-THS", method="fetch_concept_list"),
        ),
    )

    runner = PipelineRunner(reg, pipeline)
    summary = await runner.run()

    assert summary.success == 1
    assert fake_tushare.calls == [("fetch", "ALL", 1)]
    assert fake_adata.calls == ["concept_list"]


# ═══════════════════════════════════════════════════════════════════════
# 11. Runner 进度回调
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_runner_progress_callback():
    fake = FakeTushareFetcher()
    reg = DataSourceRegistry()
    reg.register_instance("Tushare", TushareAPI(fetcher=fake))

    pipeline = Pipeline(
        pipeline_id="progress_test",
        name="Progress",
        unit=UnitSpec(
            style="per_unit",
            unit_source="stock_infos",
            unit_template={"label": "{{symbol}}", "symbol": "{{symbol}}"},
        ),
        steps=(APIStep(
            name="fetch_kline",
            source="Tushare",
            method="fetch_kline",
            args_template={"symbol": "{{symbol}}", "days": 7},
        ),),
    )

    progress = []

    async def on_done(result):
        progress.append(result.detail)

    runner = PipelineRunner(reg, pipeline)
    await runner.run(params={"stock_symbols": ["a", "b", "c"]}, on_unit_done=on_done)

    assert progress == ["a", "b", "c"]


# ═══════════════════════════════════════════════════════════════════════
# 12. 默认 unit args
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_unit_default_args():
    """UnitSpec.default_unit_args 应注入 unit（如 days=7 默认）

    验证方式：用 TushareAPI 真实签名（fetch_kline 的 days 参数是 int）
    通过 Pipeline 模板渲染传入，看是否还原为 int。
    """
    from application.port.collector_port import CollectParams
    captured = []

    class CapturingTushare:
        @property
        def source_name(self):
            return "Tushare"

        @property
        def available_methods(self):
            return ["fetch_kline"]

        async def fetch_kline(self, symbol: str, days: int = 30):  # 真实签名：int
            captured.append({"symbol": symbol, "days": days})
            return CallResult.success(data=[], source="Tushare")

    reg = DataSourceRegistry()
    reg.register_instance("Tushare", CapturingTushare())

    pipeline = Pipeline(
        pipeline_id="default_args",
        name="Default Args",
        unit=UnitSpec(
            style="per_unit",
            unit_source="stock_infos",
            unit_template={"label": "{{symbol}}", "symbol": "{{symbol}}"},
            default_unit_args={"days": 7},  # ← 默认 7 天
        ),
        steps=(APIStep(
            name="fetch_kline",
            source="Tushare",
            method="fetch_kline",
            args_template={"symbol": "{{symbol}}", "days": "{{days}}"},
        ),),
    )

    runner = PipelineRunner(reg, pipeline)
    await runner.run(params={"stock_symbols": ["600519"]})

    # 验证默认 7 被填进 args，且类型正确还原为 int（不是字符串 "7"）
    assert captured == [{"symbol": "600519", "days": 7}]
