# 06 · 附录：为什么 fetcher 不做配置化

> **定位**：本文是 `03-三表重构方案.md` 的**背景论证**，不是独立方案。
> 结论已固化进 `00-概要说明.md` 的决策表和 `03` 的 §9.8「不动的部分」。
>
> **一句话结论**：性能影响≈0（用户判断正确），
> 但 fetcher 层 1484 行里约 80% 是业务逻辑，无法配置化。
> 所以采纳「fetcher 建表存元数据」，不采纳「fetcher 逻辑配置化」。

---

## 1. 需求来源

用户在初版方案后提出：

> 假设改为数据库记录接口，会不会对性能有很大影响（我觉得应该不会吧）？

**用户对性能的判断是正确的。** 本文的目的是说明**真正的障碍不是性能**。

## 1. 当前 fetcher 实现盘点（实测数据）

### 1.1 代码规模

| 文件 | 行数 | 实现方 | 实现的协议数 |
|------|------|--------|------------|
| `fetcher/tushare.py` | **939** | TushareFetcher | 16 |
| `fetcher/adata.py` | 271 | AdataConceptFetcher | 1（内部 7+ 方法） |
| `fetcher/pytdx.py` | 217 | PytdxFetcher | 1 |
| `fetcher/base.py` | 29 | BaseCollector（ABC） | — |
| `fetcher/__init__.py` | 28 | re-export | — |
| **合计** | **1484** | 3 个实现 | **18 个 Protocol** |

另有 `application/port/collector_port.py` 定义 **18 个 Protocol**（约 370 行）。

### 1.2 一个 fetch 方法实际干了几件事

以 `fetch_top_list` 为例，**它不是"一个 API 调用"，而是 5 个步骤的流水线**：

```623:641:D:\codes\Attribution_Analysis\backend\src\infrastructure\adapter\scheduler\fetcher\tushare.py
```

拆开看：

| 步骤 | 内容 | 能否配置化 |
|------|------|-----------|
| ① 参数转换 | `symbol_to_ts_code("600000")` → `"600000.SH"` | ❌ **业务规则**（83/87/43/82/92→BJ，600/601/603/605/688/689→SH，其余→SZ） |
| ② 限流识别 | `_is_rate_limit(e)` 匹配中文错误串「每分钟」「最多访问」「频率」 | ❌ **依赖第三方错误文案** |
| ③ 发起请求 | `self._pro.top_list(trade_date=...)` | ✅ 可配置 |
| ④ 空值判定 | `df is None or df.empty` → 返回 `[]` | ⚠️ 部分可配 |
| ⑤ 逐行转换 | `_row_to_top_list_bo(row)` | ❌ **手写字段映射** |

### 1.3 关键统计：解析层占大头

```
tushare.py 中 _row_to_*_bo / _parse_row 类方法：33 个
```

**这 33 个方法是整个 fetcher 层的价值所在**，也是最无法配置化的部分。例如：

```775:800:D:\codes\Attribution_Analysis\backend\src\infrastructure\adapter\fetcher\tushare.py
    @staticmethod
    def _row_to_holder_num_bo(row: pd.Series) -> Optional[Any]:
        from route.dto.request.cap_holder_num import CapHolderNumBO
        ts_code = row.get("ts_code")
        end_date = parse_list_date(row.get("end_date"))
        if not ts_code or pd.isna(ts_code) or not end_date:
            return None

        def _f(key):
            v = row.get(key)
            if v is None or pd.isna(v):
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        holder_num_raw = row.get("holder_num")
        holder_num_int = int(holder_num_raw) if holder_num_raw is not None and pd.notna(holder_num_raw) else None

        return CapHolderNumBO(
            symbol=str(ts_code).split(".")[0],
            ann_date=parse_list_date(row.get("ann_date")),
            end_date=end_date,
            holder_num=holder_num_int,
            holder_nums=_f("holder_nums"),
        )
```

每个方法都包含**四类无法写成配置的东西**：
1. **空值语义判断**（`if not ts_code or pd.isna(ts_code) or not end_date: return None` —— 什么情况丢弃这一行？）
2. **类型强制与容错**（`float(v)` 包 try/except，失败返回 None 而不是崩）
3. **日期解析多格式兼容**（`parse_list_date` 处理 `YYYYMMDD` / `0` / 空串 / `NaN` / `20240101`）
4. **业务字段变换**（`amount * 1000` 千元转元；`ts_code.split(".")[0]` 取 6 位代码）

### 1.4 还有一层：纯业务规则

```51:66:D:\codes\Attribution_Analysis\backend\src\infrastructure\adapter\fetcher\tushare.py
def _is_rate_limit(e: Exception) -> bool:
    msg = str(e)
    return "每分钟" in msg or "最多访问" in msg or "频率" in msg


def dedupe_income(df: pd.DataFrame) -> pd.DataFrame:
    """同一报告期 Tushare 会返回更正前后多行：优先 update_flag=1，其次实际公告日、公告日最新"""
    if df.empty:
        return df
    ordered = df.assign(
        _flag=df["update_flag"].fillna("0").astype(str),
        _f_ann=df["f_ann_date"].fillna("").astype(str),
        _ann=df["ann_date"].fillna("").astype(str),
    ).sort_values(["_flag", "_f_ann", "_ann"], ascending=False)
    return (
        ordered.drop_duplicates(subset=_INCOME_KEY, keep="first")
        .drop(columns=["_flag", "_f_ann", "_ann"])
        .sort_values("end_date", ascending=False)
    )
```

`dedupe_income` 是**纯 pandas 业务逻辑**（同一报告期去重，优先更正后数据）。
这种逻辑没有任何配置表达方式，只能是代码。

还有 `symbol_to_ts_code` 的交易所映射规则、`cap_holder_num` 的 `only_missing` 语义、
`concept_reason` 的入选理由去重——**全是业务知识，藏在代码里**。

---

## 2. 性能分析（回答你的直接问题）

### 2.1 你的直觉是对的

假设每次采集单元执行前都查一次 DB 拿 fetcher 配置，对比：

| 操作 | 耗时量级 |
|------|---------|
| tushare HTTP 请求 | 100 ~ 500 ms |
| pandas DataFrame 解析 | 1 ~ 50 ms |
| **一次 DB 查询（远程库）** | **5 ~ 30 ms** |

单次额外开销占比 **< 5%**，且被 HTTP 请求完全淹没。

### 2.2 但更好的做法是缓存，然后开销≈0

fetcher 定义**几乎不变**（改一次要发版才会变）。所以：

```
应用启动 → 一次性把 fetcher 定义读进内存 → 全程不查 DB
定义变更 → 通过 admin 接口 invalidate 缓存（秒级生效，无需发版）
```

**这样运行期性能开销是 0**（一次内存 dict 查找，约 100ns），
启动时多 20 行记录的加载（< 10ms）。

所以：**性能完全不是反对配置化的理由。你想对了。**

### 2.3 唯一真实的性能代价

| 代价 | 量级 | 是否可接受 |
|------|------|-----------|
| 启动加载配置 | +10 ms | ✅ 可忽略 |
| 内存驻留 20 个定义 | +几十 KB | ✅ 可忽略 |
| **首次执行时构建解析器** | 需把 DB schema 编译成 callable | ⚠️ 这是**复杂度**不是性能 |

注意最后一行：配置驱动的解析器要么**每次执行重新构建**（慢且浪费），
要么写一个**配置 → callable 的编译器**（这本身就是一个小型框架，比现在的直接代码更难维护）。

---

## 3. 真正的代价（不是性能，是可维护性）

### 3.1 解析层配置化 = 自造 DSL

要让 DB 记录表达 `_row_to_holder_num_bo`，你得设计类似这样的 schema：

```json
{
  "row_filter": "ts_code not null and end_date not null",
  "fields": {
    "symbol": {"expr": "ts_code.split('.')[0]"},
    "end_date": {"expr": "parse_date(end_date)", "on_error": "skip_row"},
    "holder_num": {"expr": "int(holder_num)", "on_error": "null"},
    "holder_nums": {"expr": "float_or_null(holder_nums)"}
  }
}
```

**这个 JSON 和直接写 Python 函数，哪个更好维护？**

- JSON 优势：改字段名不用发版
- JSON 劣势：语法错误运行时才发现；没有 IDE 补全；调试要看 DB 里的字符串；无法写复杂逻辑

**判断标准**：如果 DSL 简单到能表达全部需求，那它也简单到不需要配置化（直接写代码更短）；
如果复杂到能表达全部需求，那它就是一个需要自己写测试、自己维护的框架。

**这是经典的「配置化二难」**。你现在的 33 个 Python 方法，
就是「刚好在复杂度阈值之上」的位置——复杂到必须用代码，但还没复杂到需要框架。

### 3.2 类型安全从编译期退化到运行期

现在 `KlineBO` 是 pydantic 模型，字段类型在构造时校验：

```152:163:D:\codes\Attribution_Analysis\backend\src\infrastructure\adapter\fetcher\tushare.py
        return KlineBO(
            symbol=symbol,
            name="",
            trade_date=trade_date,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=volume,
            amount=amount_yuan,
            change_pct=change_pct,
        )
```

改成配置驱动后，字段名写错要等到**运行时读到那一行数据**才报错。
采集任务跑 5572 个单元，中途才炸，排查成本高。

### 3.3 现有 Protocol 层是好的 DDD 设计

现在的分层是标准 DDD 防腐层：

```
application/port/collector_port.py     ← 抽象（18 个 Protocol，不依赖任何 SDK）
        ↑ 实现
infrastructure/adapter/fetcher/*.py   ← 具体（依赖 tushare / pytdx / adata）
```

而且有**启动期签名校验**：

```342:356:D:\codes\Attribution_Analysis\backend\src\application\port\collector_port.py
def validate_protocol_implementation(
    instance: object,
    protocol: type[P],
) -> None:
    """校验实例是否完整实现了给定协议的所有方法签名

    在 registry.register_instance() / register_factory() 内部调用，
    也可在测试中单独使用。
    """
    for attr_name in dir(protocol):
        if attr_name.startswith("_"):
            continue
        attr = getattr(protocol, attr_name)
        if callable(attr) or isinstance(attr, property):
            _check_protocol_signature(instance, protocol, attr_name)
```

**注册时就校验签名，不匹配立刻抛 `TypeError`**。改成 DB 配置后，
这个校验要么消失，要么得再写一个"配置校验器"。

### 3.4 对你的目标没有帮助

**这是最关键的一点。**

你的原始目标是：**让某些接口按每天固定时间 / 固定频率自动采集**。

这个目标 **100% 在 plan 层解决**，与 fetcher 是否配置化**完全无关**：

| 你的需求 | 由哪层解决 | 需要动 fetcher 吗 |
|---------|-----------|------------------|
| 每天 09:30 触发 | plan + scheduler | ❌ |
| 每 5 分钟触发 | plan + scheduler | ❌ |
| 按时跑哪些接口 | plan ↔ task_type 关联 | ❌ |
| 每个接口带什么参数 | plan ↔ task_type 关联的 params | ❌ |
| **「新增一个数据源，不发版就能接入」** | fetcher 配置化 | ✅ 只有这条 |

前四条是**配置数据**（存在 DB 是对的），
第五条是**代码资产**（存 DB 是错的）。

**把代码资产存进 DB，不会让它变成数据。**

---

## 4. 提案可行性逐条判定

| 你的提案 | 判定 | 理由 |
|---------|------|------|
| `collect_plan` 表存类型 + 时间 | ✅ **可行** | 这正是 `03-三表重构方案.md` 的 `collect_plans` |
| plan ↔ 接口的关联表 | ✅ **可行且更优** | 规范化设计，比当前 `collect_plans.task_type` 单一外键更灵活 |
| 关联表存每个接口的参数 | ✅ **可行** | 这正是你想删掉的 `params`，但**放在关联表里比放在 plan 的 JSON blob 里更合理** |
| **给 fetcher 建表** | ⚠️ **元数据可以，逻辑不行** | 存"有哪些 fetcher / 叫什么 / 参数名列表"可以；存"怎么调 / 怎么解析"不行 |
| **用 DB 记录接口定义** | ❌ **不可行** | 80% 是业务逻辑（解析/映射/限流识别/去重），无法配置化 |
| 性能影响 | ✅ **≈0** | 你的判断正确，缓存后完全无开销 |

### 4.1 关于「plan ↔ 关联表」的价值

值得指出：你想引入的关联表，实际上解决了我在 `05-待确认问题.md` Q4 里提到的问题——
**`task_type` 有 unique 约束，一个接口只能配一个方案**。

```
现在：  collect_plans.task_type UNIQUE  →  一个接口只能有一条方案
提案后： collect_plans ←→ collect_plan_items ←→ (task_type + params)
                                        →  一个接口可出现在多个方案里
```

这确实更灵活。比如：
- 方案「盘前同步」：`daily_kline(days=1)` + `cap_top_list`
- 方案「盘后补数」：`daily_kline(days=7)` + `fin_top10_floatholders(only_missing=True)`

**但**这跟你本轮"删掉方案参数"的决定有张力。所以顺序上应该是：
先把定时/定频跑通 → 之后再引入关联表把参数加回来。

---

## 5. 折中方案：分层采纳

我建议**采纳提案的一半，另一半换个目标**。

### 5.1 ✅ 采纳：plan ↔ 接口关联表（未来做）

```
collect_plans          (id, name, schedule_type, times, interval_seconds, enabled)
collect_plan_items     (id, plan_id, task_type, params JSON, sort_order)
                              ↑ 关联表，记录该方案跑哪些接口 + 各自参数
```

**收益**：
- 一个接口可属于多个方案（解决 Q4）
- 参数落在正确的粒度（每个接口一份，而不是整个 plan 一份 JSON）
- 任务组 `collect_groups` 可以直接退化成"一个特殊的 plan"（合并两个概念）

**代价**：要改 `collect_plans` 主键语义（从 `task_type` 改成 `id`），
涉及 `CollectConfigRepoImpl`、`plan_to_dict`、前端、测试。

**时机**：本轮定时/定频跑通之后，作为独立一轮。

### 5.2 🔄 改变目标：fetcher 建表 → **只读元数据表**

如果你的真实动机是「**新加一个数据源不想发版**」或「**想可视化查看有哪些接口**」，
那可以建表，但表的**内容应该是元数据，不是逻辑**：

```
fetcher_catalog
  name            (如 'cap_top_list')
  protocol        ('TopListFetcher')
  impl            ('TushareFetcher')
  source          ('Tushare')
  method          ('fetch_top_list')
  params_schema   (JSON: 形如 {"trade_date": "str(YYYYMMDD)", "period": "opt[str]"})
  task_type       ('cap_top_list')
  target_table    ('cap_top_lists')
  enabled         (true)
```

**这个表的价值**：
- UI 可展示"当前系统支持哪些接口、分别打哪个数据源、写哪张表"
- 新人不用翻代码就知道有哪些接口
- 可做**执行前的 dry-run 校验**（配置了但 fetcher 没实现 → 明确报错）
- `params_schema` 可以驱动前端表单渲染（这才是真正有价值的部分）

**这个表不能做的**：
- ❌ 不能存字段映射规则（解析逻辑仍是代码）
- ❌ 不能存交易所映射规则
- ❌ 不能存限流参数（`RATE_LIMIT_WAIT=60` 这种）

**关键区别**：元数据是**描述**，逻辑是**执行**。
描述进 DB 合理，执行进 DB 是把代码变成数据。

### 5.3 ❌ 不采纳：fetcher 定义完全配置化

理由已在 §3 展开。补充一个具体风险：

**你的 fetcher 里有大量"针对第三方数据怪癖的补丁"**：

```284:291:D:\codes\Attribution_Analysis\backend\src\infrastructure\adapter\fetcher\tushare.py
        if df is None or df.empty:
            self._log("warning", f"{params.symbol}: Tushare 返回空数据")
            return []

        # 空 DataFrame 但触发了限频特征（Tushare 偶发返回空 + 限频）—— 不视为成功 0 条
        # 注：上面已 raise RateLimitError，这里只是兜底
        df = df.sort_values("trade_date").reset_index(drop=True)
        klines = self._parser.parse(df, params.symbol)
```

```96:104:D:\codes\Attribution_Analysis\backend\src\infrastructure\adapter\fetcher\tushare.py
def parse_list_date(s) -> Optional[date]:
    """YYYYMMDD 字符串 → date"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    if not s or s == "0" or s == "00000000":
        return None
    try:
        return pd.to_datetime(s, format="%Y%m%d").date()
    except Exception:
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None
```

这些注释里写着的「Tushare 偶发返回空 + 限频」「`0` 表示无效日期」，
是**踩过坑才知道的知识**。把它们翻译成配置 DSL 的过程，
既费力又会丢失这些注释携带的上下文——而这些上下文恰恰是最有价值的部分。

**配置化会让你失去"为什么这样写"的历史信息。**

---

## 6. 落地情况

| 提案部分 | 落地位置 | 状态 |
|---------|---------|------|
| plan 表存触发配置 | `collect_plans`（`schedule_type` / `times` / `interval_seconds`） | ✅ 本次做 |
| plan ↔ fetcher 关联表（带 params） | `collect_plan_items` | ✅ 本次做 |
| fetcher 元数据表 | `collect_fetchers`（只存元数据） | ✅ 本次做 |
| fetcher 逻辑配置化 | — | ❌ 不采纳 |

**如果只记一句话**：

> **配置（何时采、采什么、什么参数）进 DB；代码（怎么调、怎么解析）留在代码。**

---

## 7. 关联的待确认问题

本文的结论已固化，相关决策项见 `05-待确认问题.md`：

| # | 问题 |
|---|------|
| Q1 | `collect_plans.task_type` 的 unique 约束怎么去除（旧数据怎么办） |
| Q5 | `collect_fetchers` 要不要加 `source` 字段（代码侧目前没有这个类变量） |
| Q9 | `params_schema` / `target_table` 本轮不做，是否同意 |
