package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_top_list")
public class TopListPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private String symbol;
    private String name;
    private BigDecimal close;

    @TableField("pct_change")
    private BigDecimal pctChange;

    @TableField("turnover_rate")
    private BigDecimal turnoverRate;

    private BigDecimal amount;

    @TableField("l_sell")
    private BigDecimal lSell;

    @TableField("l_buy")
    private BigDecimal lBuy;

    @TableField("l_amount")
    private BigDecimal lAmount;

    @TableField("net_amount")
    private BigDecimal netAmount;

    @TableField("net_rate")
    private BigDecimal netRate;

    @TableField("amount_rate")
    private BigDecimal amountRate;

    @TableField("float_values")
    private BigDecimal floatValues;

    private String reason;

    @TableField("data_source")
    private String dataSource;
}
