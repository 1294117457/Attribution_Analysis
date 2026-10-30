package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_block_trade")
public class BlockTradePO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private String symbol;
    private String name;
    private BigDecimal price;
    private BigDecimal vol;
    private BigDecimal amount;
    private String buyer;
    private String seller;

    @TableField("data_source")
    private String dataSource;
}
