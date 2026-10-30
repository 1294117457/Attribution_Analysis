package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_daily_basic")
public class DailyBasicPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private BigDecimal close;

    @TableField("turnover_rate")
    private BigDecimal turnoverRate;

    @TableField("turnover_rate_f")
    private BigDecimal turnoverRateF;

    @TableField("volume_ratio")
    private BigDecimal volumeRatio;

    private BigDecimal pe;

    @TableField("pe_ttm")
    private BigDecimal peTtm;

    private BigDecimal pb;
    private BigDecimal ps;

    @TableField("ps_ttm")
    private BigDecimal psTtm;

    @TableField("dv_ratio")
    private BigDecimal dvRatio;

    @TableField("dv_ttm")
    private BigDecimal dvTtm;

    @TableField("total_share")
    private BigDecimal totalShare;

    @TableField("float_share")
    private BigDecimal floatShare;

    @TableField("free_share")
    private BigDecimal freeShare;

    @TableField("total_mv")
    private BigDecimal totalMv;

    @TableField("circ_mv")
    private BigDecimal circMv;

    @TableField("data_source")
    private String dataSource;
}
