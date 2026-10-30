## 股票基础信息

------

接口：stock_basic，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据
描述：获取基础信息数据，包括股票代码、名称、上市日期、退市日期等
限量：每次最多返回6000行数据（覆盖全市场A股，会随股票总数增长而增加）
权限：2000积分起，每分钟请求50次。此接口是基础信息，调取一次就可以拉取完，建议保存倒本地存储后使用

**输入参数**

| 名称        | 类型 | 必选 | 描述                                                         |
| :---------- | :--- | :--- | :----------------------------------------------------------- |
| ts_code     | str  | N    | TS股票代码([格式说明](https://tushare.pro/document/2?doc_id=14)) |
| name        | str  | N    | 名称                                                         |
| market      | str  | N    | 市场类别 （主板/创业板/科创板/CDR/北交所）                   |
| list_status | str  | N    | 上市状态 L上市 D退市 P暂停上市 G 未交易 UN未上市，默认是L    |
| exchange    | str  | N    | 交易所 SSE上交所 SZSE深交所 BSE北交所                        |
| is_hs       | str  | N    | 是否沪深港通标的，N否 H沪股通 S深股通                        |

**输出参数**

| 名称         | 类型 | 默认显示 | 描述                                                |
| :----------- | :--- | :------- | :-------------------------------------------------- |
| ts_code      | str  | Y        | TS代码                                              |
| symbol       | str  | Y        | 股票代码                                            |
| name         | str  | Y        | 股票名称                                            |
| area         | str  | Y        | 地域                                                |
| industry     | str  | Y        | 所属行业                                            |
| fullname     | str  | N        | 股票全称                                            |
| enname       | str  | N        | 英文全称                                            |
| cnspell      | str  | Y        | 拼音缩写                                            |
| market       | str  | Y        | 市场类型（主板/创业板/科创板/CDR）                  |
| exchange     | str  | N        | 交易所代码                                          |
| curr_type    | str  | N        | 交易货币                                            |
| list_status  | str  | N        | 上市状态 L上市 D退市 G过会未交易 P暂停上市 UN未上市 |
| list_date    | str  | Y        | 上市日期                                            |
| delist_date  | str  | N        | 退市日期                                            |
| is_hs        | str  | N        | 是否沪深港通标的，N否 H沪股通 S深股通               |
| act_name     | str  | Y        | 实控人名称                                          |
| act_ent_type | str  | Y        | 实控人企业性质                                      |

说明：旧版上的PE/PB/股本等字段，请在行情接口[“每日指标”](https://tushare.pro/document/2?doc_id=32)中获取。

## 复权因子

------

接口：adj_factor，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
更新时间：盘前9点15~20分完成当日复权因子入库
描述：本接口由Tushare自行生产，获取股票复权因子，可提取单只股票全部历史复权因子，也可以提取单日全部股票的复权因子。
积分要求：2000积分起，5000以上可高频调取

**输入参数**

| 名称       | 类型 | 必选 | 描述                     |
| :--------- | :--- | :--- | :----------------------- |
| ts_code    | str  | N    | 股票代码                 |
| trade_date | str  | N    | 交易日期(YYYYMMDD，下同) |
| start_date | str  | N    | 开始日期                 |
| end_date   | str  | N    | 结束日期                 |

**注：日期都填YYYYMMDD格式，比如20181010**

**输出参数**

| 名称       | 类型  | 必选 | 描述     |
| :--------- | :---- | :--- | :------- |
| ts_code    | str   | Y    | 股票代码 |
| trade_date | str   | Y    | 交易日期 |
| adj_factor | float | Y    | 复权因子 |

## 每日停复牌信息

------

接口：suspend_d
更新时间：不定期
描述：开始时间2000-01-03，单次查询返回5000行。至少需要2000积分 可以调用，5000积分可以获得更高的频次，按日期方式获取股票每日停复牌信息。

**输入参数**

| 名称         | 类型 | 必选 | 描述                      |
| :----------- | :--- | :--- | :------------------------ |
| ts_code      | str  | N    | 股票代码(可输入多值)      |
| trade_date   | str  | N    | 交易日日期                |
| start_date   | str  | N    | 停复牌查询开始日期        |
| end_date     | str  | N    | 停复牌查询结束日期        |
| suspend_type | str  | N    | 停复牌类型：S-停牌,R-复牌 |

**输出参数**

| 名称           | 类型 | 默认显示 | 描述                                         |
| :------------- | :--- | :------- | :------------------------------------------- |
| ts_code        | str  | Y        | TS代码                                       |
| trade_date     | str  | Y        | 停复牌日期（覆盖从停牌到覆盖期间的连续日期） |
| suspend_timing | str  | Y        | 日内停牌时间段（日内停牌才有值，否则为空值） |
| suspend_type   | str  | Y        | 停复牌类型：S-停牌，R-复牌                   |

## 股票曾用名

------

接口：namechange
描述：历史名称变更记录

**输入参数**

| 名称       | 类型 | 必选 | 描述         |
| :--------- | :--- | :--- | :----------- |
| ts_code    | str  | N    | TS代码       |
| start_date | str  | N    | 公告开始日期 |
| end_date   | str  | N    | 公告结束日期 |

**输出参数**

| 名称          | 类型 | 默认输出 | 描述     |
| :------------ | :--- | :------- | :------- |
| ts_code       | str  | Y        | TS代码   |
| name          | str  | Y        | 证券名称 |
| start_date    | str  | Y        | 开始日期 |
| end_date      | str  | Y        | 结束日期 |
| ann_date      | str  | Y        | 公告日期 |
| change_reason | str  | Y        | 变更原因 |

## 个股资金流向

------

接口：moneyflow，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取沪深A股票资金流向数据，分析大单小单成交情况，用于判别资金动向，数据开始于2010年。
限量：单次最大提取6000行记录，总量不限制
积分：用户需要至少2000积分才可以调取，基础积分有流量控制，积分越多权限越大，请自行提高积分，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)





**输入参数**

| 名称       | 类型 | 必选 | 描述                                    |
| :--------- | :--- | :--- | :-------------------------------------- |
| ts_code    | str  | N    | 股票代码 （股票和时间参数至少输入一个） |
| trade_date | str  | N    | 交易日期                                |
| start_date | str  | N    | 开始日期                                |
| end_date   | str  | N    | 结束日期                                |





**输出参数**

| 名称            | 类型  | 默认显示 | 描述                   |
| :-------------- | :---- | :------- | :--------------------- |
| ts_code         | str   | Y        | TS代码                 |
| trade_date      | str   | Y        | 交易日期               |
| buy_sm_vol      | int   | Y        | 小单买入量（手）       |
| buy_sm_amount   | float | Y        | 小单买入金额（万元）   |
| sell_sm_vol     | int   | Y        | 小单卖出量（手）       |
| sell_sm_amount  | float | Y        | 小单卖出金额（万元）   |
| buy_md_vol      | int   | Y        | 中单买入量（手）       |
| buy_md_amount   | float | Y        | 中单买入金额（万元）   |
| sell_md_vol     | int   | Y        | 中单卖出量（手）       |
| sell_md_amount  | float | Y        | 中单卖出金额（万元）   |
| buy_lg_vol      | int   | Y        | 大单买入量（手）       |
| buy_lg_amount   | float | Y        | 大单买入金额（万元）   |
| sell_lg_vol     | int   | Y        | 大单卖出量（手）       |
| sell_lg_amount  | float | Y        | 大单卖出金额（万元）   |
| buy_elg_vol     | int   | Y        | 特大单买入量（手）     |
| buy_elg_amount  | float | Y        | 特大单买入金额（万元） |
| sell_elg_vol    | int   | Y        | 特大单卖出量（手）     |
| sell_elg_amount | float | Y        | 特大单卖出金额（万元） |
| net_mf_vol      | int   | Y        | 净流入量（手）         |
| net_mf_amount   | float | Y        | 净流入额（万元）       |



各类别统计规则如下：
**小单**：5万以下 **中单**：5万～20万 **大单**：20万～100万 **特大单**：成交额>=100万 ，数据基于主动买卖单统计

注：净流入为主动买卖单的净值，基于L2订单计算，此处不能简单把大小单总和相减。

## 龙虎榜每日明细

------

接口：top_list
描述：龙虎榜每日交易明细
数据历史： 2005年至今
限量：单次请求返回最大10000行数据，可通过参数循环获取全部历史
积分：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称       | 类型 | 必选 | 描述     |
| :--------- | :--- | :--- | :------- |
| trade_date | str  | Y    | 交易日期 |
| ts_code    | str  | N    | 股票代码 |

**输出参数**

| 名称          | 类型  | 默认显示 | 描述             |
| :------------ | :---- | :------- | :--------------- |
| trade_date    | str   | Y        | 交易日期         |
| ts_code       | str   | Y        | TS代码           |
| name          | str   | Y        | 名称             |
| close         | float | Y        | 收盘价           |
| pct_change    | float | Y        | 涨跌幅           |
| turnover_rate | float | Y        | 换手率           |
| amount        | float | Y        | 总成交额         |
| l_sell        | float | Y        | 龙虎榜卖出额     |
| l_buy         | float | Y        | 龙虎榜买入额     |
| l_amount      | float | Y        | 龙虎榜成交额     |
| net_amount    | float | Y        | 龙虎榜净买入额   |
| net_rate      | float | Y        | 龙虎榜净买额占比 |
| amount_rate   | float | Y        | 龙虎榜成交额占比 |
| float_values  | float | Y        | 当日流通市值     |
| reason        | str   | Y        | 上榜理由         |

## 龙虎榜机构明细

------

接口：top_inst
描述：龙虎榜机构成交明细
限量：单次请求最大返回10000行数据，可根据参数循环获取全部历史
积分：用户需要至少5000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)





**输入参数**

| 名称       | 类型 | 必选 | 描述     |
| :--------- | :--- | :--- | :------- |
| trade_date | str  | Y    | 交易日期 |
| ts_code    | str  | N    | TS代码   |





**输出参数**

| 名称       | 类型  | 默认显示 | 描述                                                    |
| :--------- | :---- | :------- | :------------------------------------------------------ |
| trade_date | str   | Y        | 交易日期                                                |
| ts_code    | str   | Y        | TS代码                                                  |
| exalter    | str   | Y        | 营业部名称                                              |
| side       | str   | Y        | 买卖类型0：买入金额最大的前5名， 1：卖出金额最大的前5名 |
| buy        | float | Y        | 买入额（元）                                            |
| buy_rate   | float | Y        | 买入占总成交比例                                        |
| sell       | float | Y        | 卖出额（元）                                            |
| sell_rate  | float | Y        | 卖出占总成交比例                                        |
| net_buy    | float | Y        | 净成交额（元）                                          |
| reason     | str   | Y        | 上榜理由                                                |

## 大宗交易

------

接口：block_trade
描述：大宗交易
限量：单次最大1000条，总量不限制
积分：2000积分可调取，每分钟内限制次数，超过5000积分频次相对较高，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)





**输入参数**

| 名称       | 类型 | 必选 | 描述                                     |
| :--------- | :--- | :--- | :--------------------------------------- |
| ts_code    | str  | N    | TS代码（股票代码和日期至少输入一个参数） |
| trade_date | str  | N    | 交易日期（格式：YYYYMMDD，下同）         |
| start_date | str  | N    | 开始日期                                 |
| end_date   | str  | N    | 结束日期                                 |





**输出参数**

| 名称       | 类型  | 默认显示 | 描述           |
| :--------- | :---- | :------- | :------------- |
| ts_code    | str   | Y        | TS代码         |
| trade_date | str   | Y        | 交易日历       |
| price      | float | Y        | 成交价         |
| vol        | float | Y        | 成交量（万股） |
| amount     | float | Y        | 成交金额       |
| buyer      | str   | Y        | 买方营业部     |
| seller     | str   | Y        | 卖方营业部     |

## 融资融券交易明细

------

接口：margin_detail
描述：获取沪深两市每日融资融券明细，交易所于每天8点30左右更新上一日数据。**注：深交所和北交所每周五的数据在下周一上午更新。**
限量：单次请求最大返回6000行数据，可根据日期循环
权限：2000积分可获得本接口权限，积分越高权限越大，具体参考[权限说明](https://tushare.pro/document/1?doc_id=290)





**输入参数**

| 名称       | 类型 | 必选 | 描述                             |
| :--------- | :--- | :--- | :------------------------------- |
| trade_date | str  | N    | 交易日期（格式：YYYYMMDD，下同） |
| ts_code    | str  | N    | TS代码                           |
| start_date | str  | N    | 开始日期                         |
| end_date   | str  | N    | 结束日期                         |





**输出参数**

| 名称       | 类型  | 描述                          |
| :--------- | :---- | :---------------------------- |
| trade_date | str   | 交易日期                      |
| ts_code    | str   | TS股票代码                    |
| name       | str   | 股票名称 （20190910后有数据） |
| rzye       | float | 融资余额(元)                  |
| rqye       | float | 融券余额(元)                  |
| rzmre      | float | 融资买入额(元)                |
| rqyl       | float | 融券余量（股）                |
| rzche      | float | 融资偿还额(元)                |
| rqchl      | float | 融券偿还量(股)                |
| rqmcl      | float | 融券卖出量(股,份,手)          |
| rzrqye     | float | 融资融券余额(元)              |

## 沪深股通十大成交股

------

接口：hsgt_top10
描述：获取沪股通、深股通每日前十大成交详细数据，每天18~20点之间完成当日更新

**输入参数**

| 名称        | 类型 | 必选 | 描述                        |
| :---------- | :--- | :--- | :-------------------------- |
| ts_code     | str  | N    | 股票代码（二选一）          |
| trade_date  | str  | N    | 交易日期（二选一）          |
| start_date  | str  | N    | 开始日期                    |
| end_date    | str  | N    | 结束日期                    |
| market_type | str  | N    | 市场类型（1：沪市 3：深市） |

**输出参数**

| 名称        | 类型  | 必选 | 描述                        |
| :---------- | :---- | :--- | :-------------------------- |
| trade_date  | str   | Y    | 交易日期                    |
| ts_code     | str   | Y    | 股票代码                    |
| name        | str   | Y    | 股票名称                    |
| close       | float | Y    | 收盘价                      |
| change      | float | Y    | 涨跌额                      |
| rank        | int   | Y    | 资金排名                    |
| market_type | str   | Y    | 市场类型（1：沪市 3：深市） |
| amount      | float | Y    | 成交金额（元）              |
| net_amount  | float | Y    | 净成交金额（元）            |
| buy         | float | Y    | 买入金额（元）              |
| sell        | float | Y    | 卖出金额（元）              |

## 涨跌停列表（新）

------

接口：limit_list_d
描述：获取A股每日涨跌停、炸板数据情况，数据从2020年开始（不提供ST股票的统计）
限量：单次最大可以获取2500条数据，可通过日期或者股票循环提取
积分：5000积分每分钟可以请求200次每天总量1万次，8000积分以上每分钟500次每天总量不限制，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称       | 类型 | 必选 | 描述                               |
| :--------- | :--- | :--- | :--------------------------------- |
| trade_date | str  | N    | 交易日期                           |
| ts_code    | str  | N    | 股票代码                           |
| limit_type | str  | N    | 涨跌停类型（U涨停D跌停Z炸板）      |
| exchange   | str  | N    | 交易所（SH上交所SZ深交所BJ北交所） |
| start_date | str  | N    | 开始日期                           |
| end_date   | str  | N    | 结束日期                           |

**输出参数**

| 名称           | 类型  | 默认显示 | 描述                                                         |
| :------------- | :---- | :------- | :----------------------------------------------------------- |
| trade_date     | str   | Y        | 交易日期                                                     |
| ts_code        | str   | Y        | 股票代码                                                     |
| industry       | str   | Y        | 所属行业                                                     |
| name           | str   | Y        | 股票名称                                                     |
| close          | float | Y        | 收盘价                                                       |
| pct_chg        | float | Y        | 涨跌幅                                                       |
| amount         | float | Y        | 成交额                                                       |
| limit_amount   | float | Y        | 板上成交金额(成交价格为该股票跌停价的所有成交额的总和，涨停无此数据) |
| float_mv       | float | Y        | 流通市值                                                     |
| total_mv       | float | Y        | 总市值                                                       |
| turnover_ratio | float | Y        | 换手率                                                       |
| fd_amount      | float | Y        | 封单金额（以涨停价买入挂单的资金总量）                       |
| first_time     | str   | Y        | 首次封板时间（跌停无此数据）                                 |
| last_time      | str   | Y        | 最后封板时间                                                 |
| open_times     | int   | Y        | 炸板次数(跌停为开板次数)                                     |
| up_stat        | str   | Y        | 涨停统计（N/T T天有N次涨停）                                 |
| limit_times    | int   | Y        | 连板数（个股连续封板数量）                                   |
| limit          | str   | Y        | D跌停U涨停Z炸板                                              |

## 股东人数

------

接口：stk_holdernumber
描述：获取上市公司股东户数数据，数据不定期公布
限量：单次最大3000,总量不限制
积分：2000积分可调取，基础积分每分钟调取200次，5000积分以上频次相对较高。具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)





**输入参数**

| 名称       | 类型 | 必选 | 描述         |
| :--------- | :--- | :--- | :----------- |
| ts_code    | str  | N    | TS股票代码   |
| ann_date   | str  | N    | 公告日期     |
| enddate    | str  | N    | 截止日期     |
| start_date | str  | N    | 公告开始日期 |
| end_date   | str  | N    | 公告结束日期 |





**输出参数**

| 名称       | 类型 | 默认显示 | 描述       |
| :--------- | :--- | :------- | :--------- |
| ts_code    | str  | Y        | TS股票代码 |
| ann_date   | str  | Y        | 公告日期   |
| end_date   | str  | Y        | 截止日期   |
| holder_num | int  | Y        | 股东户数   |

## 每日指标

------

接口：daily_basic，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
更新时间：交易日每日15点～17点之间
描述：获取全部股票每日重要的基本面指标，可用于选股分析、报表展示等。单次请求最大返回6000条数据，可按日线循环提取全部历史。
积分：至少2000积分才可以调取，5000积分无总量限制，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称       | 类型 | 必选 | 描述                |
| :--------- | :--- | :--- | :------------------ |
| ts_code    | str  | Y    | 股票代码（二选一）  |
| trade_date | str  | N    | 交易日期 （二选一） |
| start_date | str  | N    | 开始日期(YYYYMMDD)  |
| end_date   | str  | N    | 结束日期(YYYYMMDD)  |

**注：日期都填YYYYMMDD格式，比如20181010**

**输出参数**

| 名称            | 类型  | 默认显示 | 描述                                                         |
| :-------------- | :---- | :------- | :----------------------------------------------------------- |
| ts_code         | str   | Y        | TS股票代码                                                   |
| trade_date      | str   | Y        | 交易日期                                                     |
| close           | float | Y        | 当日收盘价                                                   |
| turnover_rate   | float | Y        | 换手率（%） (成交量/无限售流通股数)                          |
| turnover_rate_f | float | Y        | 换手率（%）（自由流通股）(成交量/自由流通股数)               |
| volume_ratio    | float | Y        | 量比 VOL/MA                                                  |
| pe              | float | Y        | 市盈率（总市值/净利润， 亏损的PE为空）                       |
| pe_ttm          | float | Y        | 市盈率（ 总市值/净利润TTM，亏损的PE为空）                    |
| pb              | float | Y        | 市净率（总市值/(净资产-其他权益工具)）                       |
| ps              | float | Y        | 市销率 (总市值/营业收入(最新年报))                           |
| ps_ttm          | float | Y        | 市销率（TTM）(总市值/营业收入TTM)                            |
| dv_ratio        | float | Y        | 股息率 （%），除息日发生在去年期间的派现                     |
| dv_ttm          | float | Y        | 股息率（TTM）（%），除息日在近12个月且分红报告期在12个月以内的派现 |
| total_share     | float | Y        | 总股本 （万股）                                              |
| float_share     | float | Y        | 流通股本 （万股）                                            |
| free_share      | float | Y        | 自由流通股本 （万股）                                        |
| total_mv        | float | Y        | 总市值 （万元）                                              |
| circ_mv         | float | Y        | 流通市值（万元）                                             |
| limit_status    | int   | N        | 收盘涨跌状态：0-平盘，1-上涨(不含涨停)，2-涨停(不含一字涨停)，3-一字涨停，4-下跌(不含跌停)，5-跌停(不含一字跌停)，6-一字跌停 |

## 利润表

------

接口：income，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取上市公司财务利润表数据
积分：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

提示：当前接口只能按单只股票获取其历史数据，如果需要获取某一季度全部上市公司数据，请使用income_vip接口（参数一致），需积攒5000积分。

**输入参数**

| 名称        | 类型 | 必选 | 描述                                                         |
| :---------- | :--- | :--- | :----------------------------------------------------------- |
| ts_code     | str  | Y    | 股票代码                                                     |
| ann_date    | str  | N    | 公告日期（YYYYMMDD格式，下同）                               |
| f_ann_date  | str  | N    | 实际公告日期                                                 |
| start_date  | str  | N    | 公告日开始日期                                               |
| end_date    | str  | N    | 公告日结束日期                                               |
| period      | str  | N    | 报告期(每个季度最后一天的日期，比如20171231表示年报，20170630半年报，20170930三季报) |
| report_type | str  | N    | 报告类型，参考文档最下方说明                                 |
| comp_type   | str  | N    | 公司类型（1一般工商业2银行3保险4证券7多元金融）              |

**输出参数**

| 名称                      | 类型  | 默认显示 | 描述                                          |
| :------------------------ | :---- | :------- | :-------------------------------------------- |
| ts_code                   | str   | Y        | TS代码                                        |
| ann_date                  | str   | Y        | 公告日期                                      |
| f_ann_date                | str   | Y        | 实际公告日期                                  |
| end_date                  | str   | Y        | 报告期                                        |
| report_type               | str   | Y        | 报告类型 见底部表                             |
| comp_type                 | str   | Y        | 公司类型(1一般工商业2银行3保险4证券7多元金融) |
| end_type                  | str   | Y        | 报告期类型                                    |
| basic_eps                 | float | Y        | 基本每股收益                                  |
| diluted_eps               | float | Y        | 稀释每股收益                                  |
| total_revenue             | float | Y        | 营业总收入                                    |
| revenue                   | float | Y        | 营业收入                                      |
| int_income                | float | Y        | 利息收入                                      |
| prem_earned               | float | Y        | 已赚保费                                      |
| comm_income               | float | Y        | 手续费及佣金收入                              |
| n_commis_income           | float | Y        | 手续费及佣金净收入                            |
| n_oth_income              | float | Y        | 其他经营净收益                                |
| n_oth_b_income            | float | Y        | 加:其他业务净收益                             |
| prem_income               | float | Y        | 保险业务收入                                  |
| out_prem                  | float | Y        | 减:分出保费                                   |
| une_prem_reser            | float | Y        | 提取未到期责任准备金                          |
| reins_income              | float | Y        | 其中:分保费收入                               |
| n_sec_tb_income           | float | Y        | 代理买卖证券业务净收入                        |
| n_sec_uw_income           | float | Y        | 证券承销业务净收入                            |
| n_asset_mg_income         | float | Y        | 受托客户资产管理业务净收入                    |
| oth_b_income              | float | Y        | 其他业务收入                                  |
| fv_value_chg_gain         | float | Y        | 加:公允价值变动净收益                         |
| invest_income             | float | Y        | 加:投资净收益                                 |
| ass_invest_income         | float | Y        | 其中:对联营企业和合营企业的投资收益           |
| forex_gain                | float | Y        | 加:汇兑净收益                                 |
| total_cogs                | float | Y        | 营业总成本                                    |
| oper_cost                 | float | Y        | 减:营业成本                                   |
| int_exp                   | float | Y        | 减:利息支出                                   |
| comm_exp                  | float | Y        | 减:手续费及佣金支出                           |
| biz_tax_surchg            | float | Y        | 减:营业税金及附加                             |
| sell_exp                  | float | Y        | 减:销售费用                                   |
| admin_exp                 | float | Y        | 减:管理费用                                   |
| fin_exp                   | float | Y        | 减:财务费用                                   |
| assets_impair_loss        | float | Y        | 减:资产减值损失                               |
| prem_refund               | float | Y        | 退保金                                        |
| compens_payout            | float | Y        | 赔付总支出                                    |
| reser_insur_liab          | float | Y        | 提取保险责任准备金                            |
| div_payt                  | float | Y        | 保户红利支出                                  |
| reins_exp                 | float | Y        | 分保费用                                      |
| oper_exp                  | float | Y        | 营业支出                                      |
| compens_payout_refu       | float | Y        | 减:摊回赔付支出                               |
| insur_reser_refu          | float | Y        | 减:摊回保险责任准备金                         |
| reins_cost_refund         | float | Y        | 减:摊回分保费用                               |
| other_bus_cost            | float | Y        | 其他业务成本                                  |
| operate_profit            | float | Y        | 营业利润                                      |
| non_oper_income           | float | Y        | 加:营业外收入                                 |
| non_oper_exp              | float | Y        | 减:营业外支出                                 |
| nca_disploss              | float | Y        | 其中:减:非流动资产处置净损失                  |
| total_profit              | float | Y        | 利润总额                                      |
| income_tax                | float | Y        | 所得税费用                                    |
| n_income                  | float | Y        | 净利润(含少数股东损益)                        |
| n_income_attr_p           | float | Y        | 净利润(不含少数股东损益)                      |
| minority_gain             | float | Y        | 少数股东损益                                  |
| oth_compr_income          | float | Y        | 其他综合收益                                  |
| t_compr_income            | float | Y        | 综合收益总额                                  |
| compr_inc_attr_p          | float | Y        | 归属于母公司(或股东)的综合收益总额            |
| compr_inc_attr_m_s        | float | Y        | 归属于少数股东的综合收益总额                  |
| ebit                      | float | Y        | 息税前利润                                    |
| ebitda                    | float | Y        | 息税折旧摊销前利润                            |
| insurance_exp             | float | Y        | 保险业务支出                                  |
| undist_profit             | float | Y        | 年初未分配利润                                |
| distable_profit           | float | Y        | 可分配利润                                    |
| rd_exp                    | float | Y        | 研发费用                                      |
| fin_exp_int_exp           | float | Y        | 财务费用:利息费用                             |
| fin_exp_int_inc           | float | Y        | 财务费用:利息收入                             |
| transfer_surplus_rese     | float | Y        | 盈余公积转入                                  |
| transfer_housing_imprest  | float | Y        | 住房周转金转入                                |
| transfer_oth              | float | Y        | 其他转入                                      |
| adj_lossgain              | float | Y        | 调整以前年度损益                              |
| withdra_legal_surplus     | float | Y        | 提取法定盈余公积                              |
| withdra_legal_pubfund     | float | Y        | 提取法定公益金                                |
| withdra_biz_devfund       | float | Y        | 提取企业发展基金                              |
| withdra_rese_fund         | float | Y        | 提取储备基金                                  |
| withdra_oth_ersu          | float | Y        | 提取任意盈余公积金                            |
| workers_welfare           | float | Y        | 职工奖金福利                                  |
| distr_profit_shrhder      | float | Y        | 可供股东分配的利润                            |
| prfshare_payable_dvd      | float | Y        | 应付优先股股利                                |
| comshare_payable_dvd      | float | Y        | 应付普通股股利                                |
| capit_comstock_div        | float | Y        | 转作股本的普通股股利                          |
| net_after_nr_lp_correct   | float | N        | 扣除非经常性损益后的净利润（更正前）          |
| credit_impa_loss          | float | N        | 信用减值损失                                  |
| net_expo_hedging_benefits | float | N        | 净敞口套期收益                                |
| oth_impair_loss_assets    | float | N        | 其他资产减值损失                              |
| total_opcost              | float | N        | 营业总成本（二）                              |
| amodcost_fin_assets       | float | N        | 以摊余成本计量的金融资产终止确认收益          |
| oth_income                | float | N        | 其他收益                                      |
| asset_disp_income         | float | N        | 资产处置收益                                  |
| continued_net_profit      | float | N        | 持续经营净利润                                |
| end_net_profit            | float | N        | 终止经营净利润                                |
| update_flag               | str   | Y        | 更新标识                                      |

## 前十大股东

------

接口：top10_holders
描述：获取上市公司前十大股东数据，包括持有数量和比例等信息
积分：需2000积分以上才可以调取本接口，5000积分以上频次会更高

**输入参数**

| 名称       | 类型 | 必选 | 描述                                           |
| :--------- | :--- | :--- | :--------------------------------------------- |
| ts_code    | str  | Y    | TS代码                                         |
| period     | str  | N    | 报告期（YYYYMMDD格式，一般为每个季度最后一天） |
| ann_date   | str  | N    | 公告日期                                       |
| start_date | str  | N    | 报告期开始日期                                 |
| end_date   | str  | N    | 报告期结束日期                                 |

**输出参数**

| 名称             | 类型  | 描述              |
| :--------------- | :---- | :---------------- |
| ts_code          | str   | TS股票代码        |
| ann_date         | str   | 公告日期          |
| end_date         | str   | 报告期            |
| holder_name      | str   | 股东名称          |
| hold_amount      | float | 持有数量（股）    |
| hold_ratio       | float | 占总股本比例(%)   |
| hold_float_ratio | float | 占流通股本比例(%) |
| hold_change      | float | 持股变动          |
| holder_type      | str   | 股东类型          |

## 前十大流通股东

------

接口：top10_floatholders
描述：获取上市公司前十大流通股东数据
积分：需2000积分以上才可以调取本接口，5000积分以上频次会更高

**输入参数**

| 名称       | 类型 | 必选 | 描述                                           |
| :--------- | :--- | :--- | :--------------------------------------------- |
| ts_code    | str  | Y    | TS代码                                         |
| period     | str  | N    | 报告期（YYYYMMDD格式，一般为每个季度最后一天） |
| ann_date   | str  | N    | 公告日期                                       |
| start_date | str  | N    | 报告期开始日期                                 |
| end_date   | str  | N    | 报告期结束日期                                 |

**输出参数**

| 名称             | 类型  | 描述                                 |
| :--------------- | :---- | :----------------------------------- |
| ts_code          | str   | TS股票代码                           |
| ann_date         | str   | 公告日期                             |
| end_date         | str   | 报告期                               |
| holder_name      | str   | 股东名称                             |
| hold_amount      | float | 持有数量（股）                       |
| hold_ratio       | float | 占总股本比例(%)                      |
| hold_float_ratio | float | 占流通股本比例(%)                    |
| hold_change      | float | 持股变动（0表示不变，空值表示 新进） |
| holder_type      | str   | 股东类型                             |

## 分红送股

------

接口：dividend
描述：分红送股数据
权限：起始时间2000-01-01，单次查询返回2000行，每日20点~21点更新，用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称         | 类型 | 必选 | 描述         |
| :----------- | :--- | :--- | :----------- |
| ts_code      | str  | N    | TS代码       |
| ann_date     | str  | N    | 公告日       |
| record_date  | str  | N    | 股权登记日期 |
| ex_date      | str  | N    | 除权除息日   |
| imp_ann_date | str  | N    | 实施公告日   |



以上参数至少有一个不能为空





**输出参数**

| 名称         | 类型  | 默认显示 | 描述               |
| :----------- | :---- | :------- | :----------------- |
| ts_code      | str   | Y        | TS代码             |
| end_date     | str   | Y        | 分红年度           |
| ann_date     | str   | Y        | 公告日(预案，决案) |
| div_proc     | str   | Y        | 实施进度           |
| stk_div      | float | Y        | 每股送转           |
| stk_bo_rate  | float | Y        | 每股送股比例       |
| stk_co_rate  | float | Y        | 每股转增比例       |
| cash_div     | float | Y        | 每股分红（税后）   |
| cash_div_tax | float | Y        | 每股分红（税前）   |
| record_date  | str   | Y        | 股权登记日         |
| ex_date      | str   | Y        | 除权除息日         |
| pay_date     | str   | Y        | 派息日             |
| div_listdate | str   | Y        | 红股上市日         |
| imp_ann_date | str   | Y        | 实施公告日         |
| base_date    | str   | N        | 基准日             |
| base_share   | float | N        | 基准股本（万）     |

## A股日线行情

------

接口：daily，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据
 数据说明：交易日每天15点～16点之间入库。本接口是未复权行情，停牌期间不提供数据
 调取说明：基础积分每分钟内可调取500次，每次6000条数据，一次请求相当于提取一个股票23年历史
 描述：获取股票行情数据，或通过[**通用行情接口**](https://tushare.pro/document/2?doc_id=109)获取数据，包含了前后复权数据

**输入参数**

| 名称       | 类型 | 必选 | 描述                                       |
| ---------- | ---- | ---- | ------------------------------------------ |
| ts_code    | str  | N    | 股票代码（支持多个股票同时提取，逗号分隔） |
| trade_date | str  | N    | 交易日期（YYYYMMDD）                       |
| start_date | str  | N    | 开始日期(YYYYMMDD)                         |
| end_date   | str  | N    | 结束日期(YYYYMMDD)                         |

**注：日期都填YYYYMMDD格式，比如20181010**

**输出参数**

| 名称       | 类型  | 默认显示 | 描述                                                         |
| ---------- | ----- | -------- | ------------------------------------------------------------ |
| ts_code    | str   | Y        | 股票代码                                                     |
| trade_date | str   | Y        | 交易日期                                                     |
| open       | float | Y        | 开盘价                                                       |
| high       | float | Y        | 最高价                                                       |
| low        | float | Y        | 最低价                                                       |
| close      | float | Y        | 收盘价                                                       |
| pre_close  | float | Y        | 昨收价【除权价】                                             |
| change     | float | Y        | 涨跌额                                                       |
| pct_chg    | float | Y        | 涨跌幅（%） 【基于除权后的昨收计算的涨跌幅：（今收-除权昨收）/除权昨收 】 |
| vol        | float | Y        | 成交量 （手）                                                |
| amount     | float | Y        | 成交额 （千元）                                              |
| ah_vol     | float | N        | 盘后成交量 （手）                                            |
| ah_amount  | float | N        | 盘后成交额 （千元）                                          |