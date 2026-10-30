package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_market_daily")
public class MarketDailyPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String market;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private BigDecimal close;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;

    @TableField("pre_close")
    private BigDecimal preClose;

    private BigDecimal change;

    @TableField("pct_chg")
    private BigDecimal pctChg;

    private BigDecimal vol;
    private BigDecimal amount;

    @TableField("data_source")
    private String dataSource;
}
