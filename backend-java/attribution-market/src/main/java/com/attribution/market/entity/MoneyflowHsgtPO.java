package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 沪深港通资金流向（北向 / 南向）。
 *
 * <p>表 {@code raw_data.capital_moneyflow_hsgt}。
 *
 * <p>结构 = Tushare {@code moneyflow_hsgt} 官方接口列（2025-10-29 实测核对）：
 * trade_date, ggt_ss, ggt_sz, hgt, sgt, north_money, south_money。
 *
 * <p>★ 一行 = 一个交易日的资金流汇总（上游**不是**按股票排行的）。
 *
 * <p>⚠️ 原 PO 的 {@code exchange} / {@code buyAmount} / {@code sellAmount}
 * 是本地自造字段，与上游和远端表**都对不上** → 已按上游重建。
 *
 * <p>⚠️ 单位：上游数值为**百万元**。
 */
@Data
@TableName("capital_moneyflow_hsgt")
public class MoneyflowHsgtPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    /** 港股通（上海）成交金额（百万元） */
    @TableField("ggt_ss")
    private BigDecimal ggtSs;

    /** 港股通（深圳）成交金额（百万元） */
    @TableField("ggt_sz")
    private BigDecimal ggtSz;

    /** 沪股通（百万元） */
    private BigDecimal hgt;

    /** 深股通（百万元） */
    private BigDecimal sgt;

    /** 北向资金（百万元） */
    private BigDecimal northMoney;

    /** 南向资金（百万元） */
    private BigDecimal southMoney;

    private String dataSource;
}
