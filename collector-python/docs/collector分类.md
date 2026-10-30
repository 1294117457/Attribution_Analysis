# 三种 collector 类型划分

判断依据：表主键是否含日期（`trade_date/end_date` 在 UK 里 = 增量；无日期 UK = 全量快照；无表 = 实时）。

## 类型一：增量采集入库 —— 17 个，全部统一暴露时间范围

主键都含日期，同一主键重复写入是 upsert 覆盖，天然支持“补历史 + 每日追加”。前端统一给 `start_date/end_date`（默认近 30 天/当日）：

| service               | 主键（含日期）                    | 官方时间参数（tushare.md）                                 | 当前缺口                                                     |
| :-------------------- | :-------------------------------- | :--------------------------------------------------------- | :----------------------------------------------------------- |
| `daily_kline`         | `(symbol, date)`                  | `trade_date/start/end_date`（行 740）                      | ✅ 已有 `start/end_date`，标杆                                |
| `adj_factor`          | `(symbol, trade_date)`            | `trade_date/start/end_date`（行 56）                       | 缺 `start/end_date`，需补                                    |
| `suspend`             | `(symbol?, trade_date)`           | `trade_date/start/end_date`（行 83）                       | 缺区间，需补                                                 |
| `name_change`         | `(symbol, start_date)`            | `start_date/end_date` 公告日期（行 108）                   | 无参数，需补（语义=公告日期，需注明）                        |
| `moneyflow`           | `(symbol, trade_date)`            | `trade_date/start/end_date`（行 140）                      | 缺区间，需补                                                 |
| `moneyflow_hsgt`      | `(trade_date, exchange)`          | `trade_date/start/end_date`（参考 hsgt 口径）              | 缺区间，需补                                                 |
| `top_list`            | `(trade_date, symbol, reason)`    | `trade_date` 必填单天（行 196）                            | 官方只支持单天，由 tasks 层按天循环                          |
| `top_inst`            | `(trade_date, …)`                 | `trade_date` 必填单天（行 234）                            | 同上，按天循环                                               |
| `block_trade`         | 明细无 UK（按天追加）             | 四者全有（行 276）                                         | 缺区间，需补                                                 |
| `margin`              | `(exchange_id, trade_date)`       | 四者全有（行 312）                                         | 缺区间，需补                                                 |
| `hsgt_top10`          | `(trade_date, symbol)`            | 四者全有（行 348）                                         | 缺区间，需补                                                 |
| `limit_list_d`        | `(trade_date, symbol)`            | 四者全有（行 384）                                         | 缺区间，需补                                                 |
| `daily_basic`         | `(symbol, trade_date)`            | `trade_date/start/end_date`（行 462）                      | 缺区间，需补                                                 |
| `fin_income`          | `(symbol, end_date, report_type)` | `start_date/end_date` 公告日期（行 507）                   | 缺区间，需补（语义=公告日期）                                |
| `top10_holders`       | `(symbol, end_date, …)`           | `period/start/end_date` 报告期（行 630）                   | 缺区间，需补（语义=报告期）                                  |
| `top10_floatholders`  | 同上                              | 同上（行 660）                                             | 同上                                                         |
| `dividend`            | `(symbol, end_date, div_proc)`    | 只有 `ann_date/record_date/ex_date` 单点（行 692），无区间 | fetcher 按 symbol 全拉；时间范围做入库后按 ann_date 过滤（或前端隐藏时间、直接全量） |
| `holder_number`       | `(symbol, end_date)`              | `ann_date/start/end_date`（行 430）                        | 缺区间，需补（语义=公告日期）                                |
| `concept_index_daily` | `(index_code, trade_date)`        | adata 无日期参数，全拉再切                                 | `start/end_date` 做库内过滤（全拉→只存范围内）               |
| `news`                | `(source, url)` 去重              | 只有 `minutes` 回溯                                        | 时间范围 = 回溯窗口，前端暴露 `minutes`/“近 N 天”换算即可    |

> 注：`news` 主键是去重键不是日期，但语义是增量追加，归入此类；前端给“近 N 天”换算成 `minutes` 即可。

## 类型二：全量覆盖 —— 4 个，不给时间范围，一键全量

无日期主键，每次都是快照覆盖，传时间无意义：

| service           | 说明                                                         |
| :---------------- | :----------------------------------------------------------- |
| `stock_basic`     | 全 A 快照（`list_status=L`），“调一次存本地”，官方无时间参数（tushare.md:11） |
| `stock_concepts`  | adata 单股所属概念快照（adata.md:70），无日期                |
| `concept_list`    | adata 概念清单快照（adata.md:10），无日期                    |
| `concept_members` | adata 概念成分快照（adata.md:32），成分每周变，定期全量覆盖  |

前端：隐藏时间组件，只留“开始全量采集”按钮 + `concurrency`。

## 类型三：实时查询 —— 4 个，不入库，不进采集页

| service            | 说明                                                         |
| :----------------- | :----------------------------------------------------------- |
| `minute_kline`     | pytdx 分 K，只走 `GET /collect/query/minute_kline`（`days/interval` 是查询窗口，不是采集范围） |
| `concept_minute`   | adata 概念分时，只走 query                                   |
| `concept_snapshot` | adata 概念实时快照，只走 query                               |
| `sentiment`        | 空壳占位，目录已隐藏                                         |

## 落到前端：一套时间组件，两套文案

- 增量类（17+news）：显示统一的 `start_date/end_date` 选择器；其中 `fin_income/holder_number` 标注“公告日期范围”，`top10_*` 标注“报告期范围”，`news` 换成“近 N 天”→`minutes`，`dividend/concept_index_daily` 标注“全拉后按范围过滤”。
- 全量类（4 个）：不显示时间，只显示“将全量覆盖”的横幅（现有 `full-mode-banner` 保留）。
- 实时类：不出现在采集页，只在 `RealtimePanel` 试查。

这样 `trade_date` 单点参数可以整体下线：增量类统一走 `start/end_date`（单天 = 起止同一天），tasks 层对 `top_list/top_inst` 这类单天接口做按天循环展开即可。