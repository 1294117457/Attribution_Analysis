package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 沪深股通每日十大成交股。
 *
 * <p>表 {@code raw_data.capital_hsgt_top10}。
 *
 * <p>结构 = Tushare {@code hsgt_top10} 官方接口列（2025-10-29 实测核对）：
 * trade_date, ts_code, name, close, change, rank, market_type,
 * amount, net_amount, buy, sell。
 *
 * <p>⚠️ 原 PO 的 {@code holdingDays} / {@code shareRatio} / {@code holdAmount}
 * 是本地自造字段，Tushare 上游**不提供** → 永远为 null，已删除。
 */
@Data
@TableName("capital_hsgt_top10")
public class HsgtTop10PO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private String symbol;
    private String name;

    /** 市场类型：1=沪市 3=深市 */
    private String marketType;

    /** 资金排名 1-10 */
    private Integer rank;

    /** 收盘价 */
    private BigDecimal close;

    /** 涨跌额 */
    @TableField("change")
    private BigDecimal change;

    /** 成交金额（元） */
    private BigDecimal amount;

    /** 净成交金额（元） */
    private BigDecimal netAmount;

    /** 买入金额（元） */
    private BigDecimal buy;

    /** 卖出金额（元） */
    private BigDecimal sell;

    private String dataSource;
}
