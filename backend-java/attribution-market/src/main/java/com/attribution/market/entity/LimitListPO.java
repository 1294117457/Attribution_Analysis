package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 每日涨跌停板。
 *
 * <p>表 {@code raw_data.capital_limit_list_d}。
 *
 * <p>结构 = Tushare {@code limit_list_d} 官方接口列（对齐
 * {@code collector-python/docs/data/tushare.md}「涨跌停列表（新）」）。
 *
 * <p>⚠️ 原 PO 的 {@code closePrice} / {@code changeRate} / {@code boardCount} /
 * {@code firstLimitTime} / {@code boardStrength} / {@code reason}
 * 是本地自造字段，Tushare 上游**不提供** → 永远为 null，已删除。
 * 官方对应字段：close→收盘价、pct_chg→涨跌幅、limit_times→连板数、
 * first_time→首次封板时间、limit→涨跌停类型。
 *
 * <p>⚠️ 当前 TUSHARE_TOKEN 无 {@code limit_list_d} 接口权限，采集需账号开通积分。
 */
@Data
@TableName("capital_limit_list_d")
public class LimitListPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private String symbol;
    private String name;
    private String industry;

    /** 收盘价 */
    private BigDecimal close;

    /** 涨跌幅（%） */
    @TableField("pct_chg")
    private BigDecimal pctChg;

    /** 成交额 */
    private BigDecimal amount;

    /** 换手率 */
    @TableField("turnover_ratio")
    private BigDecimal turnoverRatio;

    /** 流通市值 */
    @TableField("float_mv")
    private BigDecimal floatMv;

    /** 总市值 */
    @TableField("total_mv")
    private BigDecimal totalMv;

    /** 涨跌停类型：U涨停 D跌停 Z炸板 */
    @TableField("limit_type")
    private String limitType;

    /** 连板数 */
    @TableField("limit_times")
    private Integer limitTimes;

    /** 炸板次数 */
    @TableField("open_times")
    private Integer openTimes;

    /** 涨停统计（N/T T天有N次涨停） */
    @TableField("up_stat")
    private String upStat;

    /** 板上成交金额 */
    @TableField("limit_amount")
    private BigDecimal limitAmount;

    /** 封单金额 */
    @TableField("fd_amount")
    private BigDecimal fdAmount;

    /** 首次封板时间 */
    @TableField("first_time")
    private String firstTime;

    /** 最后封板时间 */
    @TableField("last_time")
    private String lastTime;

    private String dataSource;
}
