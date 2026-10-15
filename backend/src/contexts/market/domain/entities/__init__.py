"""market.domain.entities - 所有领域模型聚合

按领域模型组织，每个聚合根一个子目录，包含 entity.py、vo.py（可选）、repository.py。

22 个聚合根：
- kline, stock_info, panel
- fin_top10_holders, fin_top10_float, fin_report, fin_daily_basic
- cap_top_list, cap_top_inst, cap_moneyflow, cap_margin,
  cap_margin_detail, cap_holder_num, cap_block_trade
- base_suspend, base_name_change, base_adj_factor, base_dividend
- mkt_calendar, mkt_index_member, mkt_market_daily, mkt_sector_daily
"""
