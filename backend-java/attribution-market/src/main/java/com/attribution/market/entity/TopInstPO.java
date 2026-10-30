package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_top_inst")
public class TopInstPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private String symbol;
    private String exalter;
    private String side;
    private BigDecimal buy;

    @TableField("buy_rate")
    private BigDecimal buyRate;

    private BigDecimal sell;

    @TableField("sell_rate")
    private BigDecimal sellRate;

    @TableField("net_buy")
    private BigDecimal netBuy;

    private String reason;

    @TableField("data_source")
    private String dataSource;
}
